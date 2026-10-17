#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "game/save_file.h"
#include "game/village_props.h"
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

// The stone wall needs a town center of the second level.
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

// The corner of a square of `side` x `side` cells near the town center (`from`
// meters away or more) where a palisade fits on every module: open, level
// ground to trace on.
std::pair<std::int32_t, std::int32_t> open_ground(const Game& g, std::int32_t side, std::int32_t from = 12) {
    const DefIndex palisade = building(g, "core:palisade");
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    for (std::int32_t r = from; r < 200; r += 4) {
        for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{-r, 0}, std::pair{0, r}, std::pair{0, -r}, std::pair{r, r},
                                     std::pair{-r, -r}, std::pair{r, -r}, std::pair{-r, r}}) {
            const std::int32_t x0 = ((tc->x + dx) / 2) * 2, z0 = ((tc->z + dz) / 2) * 2;
            bool free = true;
            for (std::int32_t z = z0; z < z0 + side && free; z += 2) {
                for (std::int32_t x = x0; x < x0 + side && free; x += 2) {
                    free = g.can_place(0, palisade, x, z, 0) == PlaceError::None;
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

Command trace(const Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool z_first = false) {
    Command c;
    c.type = CommandType::Trace;
    c.def = building(g, def);
    c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
    c.value = x1;
    c.value2 = z1;
    c.count = z_first ? 1 : 0;
    return c;
}

// The buildings of a definition, by their corner cell.
std::vector<std::pair<std::int32_t, std::int32_t>> where(const Game& g, const char* def, bool complete_only = false) {
    const DefIndex d = building(g, def);
    std::vector<std::pair<std::int32_t, std::int32_t>> out;
    for (const Building& b : g.buildings().data()) {
        if (b.def == d && (!complete_only || b.state == BuildingState::Complete)) {
            out.emplace_back(b.x, b.z);
        }
    }
    std::sort(out.begin(), out.end());
    return out;
}

const Building* at(const Game& g, std::int32_t x, std::int32_t z) {
    for (const Building& b : g.buildings().data()) {
        if (x >= b.x && x < b.x + b.width && z >= b.z && z < b.z + b.depth) {
            return &b;
        }
    }
    return nullptr;
}

std::int32_t stored(const Game& g, const char* resource) {
    return g.stored(0)[g.content().find_resource(resource)];
}

}  // namespace

TEST_SUITE("trace") {
    TEST_CASE("a trace is a straight, an L or a diagonal of modules on the even lattice") {
        using Cells = std::vector<std::pair<std::int32_t, std::int32_t>>;
        // Straight, either way; the ends are their modules (odd cells snap down).
        CHECK(trace_cells(10, 20, 16, 20, false, false) == Cells{{10, 20}, {12, 20}, {14, 20}, {16, 20}});
        CHECK(trace_cells(16, 20, 10, 20, false, false) == Cells{{16, 20}, {14, 20}, {12, 20}, {10, 20}});
        CHECK(trace_cells(11, 21, 11, 25, false, false) == Cells{{10, 20}, {10, 22}, {10, 24}});
        CHECK(trace_cells(10, 20, 10, 20, false, true) == Cells{{10, 20}});
        // An L: along x first, or along z first; the corner is laid once.
        CHECK(trace_cells(10, 20, 14, 24, false, false) == Cells{{10, 20}, {12, 20}, {14, 20}, {14, 22}, {14, 24}});
        CHECK(trace_cells(10, 20, 14, 24, true, false) == Cells{{10, 20}, {10, 22}, {10, 24}, {12, 24}, {14, 24}});
        // A diagonal where the wall takes one and the ends are as far on both sides.
        CHECK(trace_cells(10, 20, 14, 24, false, true) == Cells{{10, 20}, {12, 22}, {14, 24}});
        CHECK(trace_cells(10, 20, 6, 24, true, true) == Cells{{10, 20}, {8, 22}, {6, 24}});
        CHECK(trace_cells(10, 20, 16, 24, false, true).size() == 6);  // Not as far: an L.
        // Never longer than the limit.
        const Cells longest = trace_cells(0, 0, 1000, 0, false, false);
        CHECK(longest.size() == kMaxTrace);
        CHECK(longest.back() == std::pair<std::int32_t, std::int32_t>{static_cast<std::int32_t>(kMaxTrace - 1) * 2, 0});
        CHECK(trace_cells(0, 0, 1000, 1000, false, false).size() == kMaxTrace);
    }

    TEST_CASE("each module shows the piece its four neighbors ask for") {
        using props::LineLook;
        const auto look = [](const char* arms) {
            const std::string a(arms);
            const auto has = [&](char c) { return a.find(c) != std::string::npos; };
            return props::line_look(has('E'), has('N'), has('W'), has('S'));
        };
        CHECK(look("") == LineLook{LinePiece::Pillar, 0});
        CHECK(look("W") == LineLook{LinePiece::End, 0});
        CHECK(look("S") == LineLook{LinePiece::End, 1});
        CHECK(look("E") == LineLook{LinePiece::End, 2});
        CHECK(look("N") == LineLook{LinePiece::End, 3});
        CHECK(look("EW") == LineLook{LinePiece::Straight, 0});
        CHECK(look("NS") == LineLook{LinePiece::Straight, 1});
        CHECK(look("EN") == LineLook{LinePiece::Corner, 0});
        CHECK(look("NW") == LineLook{LinePiece::Corner, 1});
        CHECK(look("WS") == LineLook{LinePiece::Corner, 2});
        CHECK(look("ES") == LineLook{LinePiece::Corner, 3});
        CHECK(look("ENW") == LineLook{LinePiece::Tee, 0});
        CHECK(look("NWS") == LineLook{LinePiece::Tee, 1});
        CHECK(look("EWS") == LineLook{LinePiece::Tee, 2});
        CHECK(look("ENS") == LineLook{LinePiece::Tee, 3});
        CHECK(look("ENWS") == LineLook{LinePiece::Cross, 0});
    }

    TEST_CASE("the base game's palisade goes in lines, with its pieces, gate and postern") {
        const Content& c = test::core_content();
        const BuildingDef& palisade = c.buildings[c.find_building("core:palisade")];
        CHECK(palisade.line == "palisade");
        CHECK(palisade.line_diagonal);
        for (std::size_t p = 0; p < kLinePieces; ++p) {
            CHECK_MESSAGE(!palisade.line_pieces[p].empty(), p);
        }
        // Salvador's numbers: 4 logs and 40 of work a module, 400 of health, and it burns.
        REQUIRE(palisade.cost.size() == 1);
        CHECK(palisade.cost[0].resource == c.find_resource("core:log"));
        CHECK(palisade.cost[0].amount == 4);
        CHECK(palisade.build_work == 40);
        CHECK(palisade.hp == 400);
        CHECK_FALSE(palisade.fireproof);
        CHECK(palisade.width == kTraceModule);
        CHECK(palisade.depth == kTraceModule);
        for (const char* id : {"core:palisade_gate", "core:palisade_postern"}) {
            const DefIndex d = c.find_building(id);
            REQUIRE_MESSAGE(d != kNoDef, id);
            CHECK_MESSAGE(c.buildings[d].line == "palisade", id);
            CHECK_MESSAGE(c.buildings[d].gate, id);
        }
        CHECK(c.buildings[c.find_building("core:palisade_gate")].width == 4);
        CHECK(c.buildings[c.find_building("core:palisade_postern")].width == 2);
        // The stone wall is traced too, with the model it had; it takes no diagonals.
        const BuildingDef& stone = c.buildings[c.find_building("core:stone_wall")];
        CHECK(stone.line == "stone");
        CHECK_FALSE(stone.line_diagonal);
        CHECK(stone.line_pieces[static_cast<std::size_t>(LinePiece::Straight)].empty());
        // A house is not a line.
        CHECK(c.buildings[c.find_building("core:house")].line.empty());
    }

    TEST_CASE("a trace of ten modules lays ten sites, and building them takes forty logs") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 24);
        grant(g, "core:log", 200);
        const std::int32_t logs = stored(g, "core:log");
        const auto rejected = g.rejected_commands();
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 18, z0));
        CHECK(g.rejected_commands() == rejected);
        const auto laid = where(g, "core:palisade");
        REQUIRE(laid.size() == 10);
        for (std::size_t i = 0; i < laid.size(); ++i) {
            CHECK(laid[i] == std::pair<std::int32_t, std::int32_t>{x0 + 2 * static_cast<std::int32_t>(i), z0});
        }
        CHECK(where(g, "core:palisade", true).empty());  // Sites: the laborers build them.
        CHECK(stored(g, "core:log") == logs);            // Nothing is paid before it is built.
        for (int i = 0; i < 400 && where(g, "core:palisade", true).size() < 10; ++i) {
            run(g, 50);
        }
        CHECK(where(g, "core:palisade", true).size() == 10);
        CHECK(stored(g, "core:log") == logs - 40);
    }

    TEST_CASE("what does not fit is left out, and the rest is laid") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 24);
        // Something already stands in the way of the line.
        Command house;
        house.type = CommandType::PlaceBuilding;
        house.def = building(g, "core:palisade");
        house.position = {Fixed::from_int(x0 + 6), Fixed::from_int(z0)};
        g.apply(house);
        REQUIRE(where(g, "core:palisade").size() == 1);
        const auto rejected = g.rejected_commands();
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 12, z0));
        CHECK(g.rejected_commands() == rejected);
        CHECK(where(g, "core:palisade").size() == 7);  // Six new ones around the one that was there.
        // A trace where nothing fits is refused whole.
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 12, z0));
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(where(g, "core:palisade").size() == 7);
        // Only what goes in lines can be traced, and only modules.
        g.apply(trace(g, "core:house", x0, z0 + 10, x0 + 12, z0 + 10));
        g.apply(trace(g, "core:palisade_gate", x0, z0 + 10, x0 + 12, z0 + 10));
        CHECK(g.rejected_commands() == rejected + 3);
        // The stone wall takes no diagonal: as far on both sides, it is laid as an L.
        g.apply(trace(g, "core:stone_wall", x0, z0 + 6, x0 + 6, z0 + 12));
        CHECK(where(g, "core:stone_wall").empty());  // And needs a larger town center.
        CHECK(g.rejected_commands() == rejected + 4);
        level_up(g);
        g.apply(trace(g, "core:stone_wall", x0, z0 + 6, x0 + 6, z0 + 12));
        CHECK(where(g, "core:stone_wall").size() == 7);
        g.apply(trace(g, "core:palisade", x0 + 12, z0 + 6, x0 + 18, z0 + 12));
        CHECK(where(g, "core:palisade").size() == 7 + 4);
    }

    TEST_CASE("an enclosure with straight and diagonal stretches lets nobody in, until it has a gate") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 28);
        // An octagon: four straight sides joined by four diagonals.
        //        (8,0)-(16,0)
        //   (0,8)            (24,8)
        //   (0,16)           (24,16)
        //        (8,24)-(16,24)
        const auto lay = [&](int ax, int az, int bx, int bz) { g.apply(trace(g, "core:palisade", x0 + ax, z0 + az, x0 + bx, z0 + bz)); };
        lay(8, 0, 16, 0);
        lay(16, 0, 24, 8);
        lay(24, 8, 24, 16);
        lay(24, 16, 16, 24);
        lay(16, 24, 8, 24);
        lay(8, 24, 0, 16);
        lay(0, 16, 0, 8);
        lay(0, 8, 8, 0);
        const FixedVec2 inside{Fixed::from_int(x0 + 13), Fixed::from_int(z0 + 13)};
        const FixedVec2 outside{Fixed::from_int(x0 - 6), Fixed::from_int(z0 - 6)};
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(g.nav().connected(outside, g.door(*tc)));
        CHECK_FALSE(g.nav().connected(inside, outside));
        // Every module blocks the way, sites included, and counts as something to break.
        for (const auto& [x, z] : where(g, "core:palisade")) {
            CHECK_FALSE(g.nav().walkable(x / 2, z / 2));
            CHECK(g.nav().obstacle(x / 2, z / 2));
        }
        // A gate set into the north side: it takes the place of two modules, and opens the way.
        const DefIndex gate = building(g, "core:palisade_gate");
        const std::size_t before = where(g, "core:palisade").size();
        REQUIRE(g.can_place(0, gate, x0 + 10, z0, 0) == PlaceError::None);
        CHECK(g.replaced_by(0, g.content().buildings[gate], x0 + 10, z0, 0).size() == 2);
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = gate;
        c.position = {Fixed::from_int(x0 + 10), Fixed::from_int(z0)};
        g.apply(c);
        CHECK(where(g, "core:palisade").size() == before - 2);
        REQUIRE(where(g, "core:palisade_gate").size() == 1);
        CHECK(g.nav().walkable((x0 + 10) / 2, z0 / 2));
        CHECK(g.nav().connected(inside, outside));
    }

    TEST_CASE("a gate only takes the place of its own wall's modules") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 24);
        level_up(g);
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 10, z0));
        g.apply(trace(g, "core:stone_wall", x0, z0 + 8, x0 + 10, z0 + 8));
        REQUIRE(where(g, "core:stone_wall").size() == 6);
        const DefIndex gate = building(g, "core:palisade_gate");
        const DefIndex postern = building(g, "core:palisade_postern");
        const DefIndex palisade = building(g, "core:palisade");
        // Over the palisade: yes, turned either way that covers it. Over the stone wall: no.
        CHECK(g.can_place(0, gate, x0 + 2, z0, 0) == PlaceError::None);
        CHECK(g.can_place(0, gate, x0 + 2, z0 + 8, 0) == PlaceError::Blocked);
        // Half on the wall and half on open ground is fine: the gate ends the wall.
        CHECK(g.can_place(0, gate, x0 + 10, z0, 0) == PlaceError::None);
        // A postern takes one module.
        CHECK(g.replaced_by(0, g.content().buildings[postern], x0 + 4, z0, 0).size() == 1);
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = postern;
        c.position = {Fixed::from_int(x0 + 4), Fixed::from_int(z0)};
        g.apply(c);
        REQUIRE(where(g, "core:palisade_postern").size() == 1);
        CHECK(where(g, "core:palisade").size() == 5);
        // Nothing takes the place of a gate: not another gate, not the wall traced over it.
        CHECK(g.can_place(0, gate, x0 + 4, z0, 0) == PlaceError::Blocked);
        CHECK(g.can_place(0, palisade, x0 + 4, z0, 0) == PlaceError::Blocked);
        CHECK(g.replaced_by(0, g.content().buildings[palisade], x0 + 2, z0, 0).empty());
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 10, z0));
        CHECK(where(g, "core:palisade_postern").size() == 1);
        CHECK(where(g, "core:palisade").size() == 5);
        // The modules a gate replaces give their materials back to the town.
        grant(g, "core:log", 100);
        for (int i = 0; i < 400 && where(g, "core:palisade", true).size() < 5; ++i) {
            run(g, 50);
        }
        REQUIRE(where(g, "core:palisade", true).size() == 5);
        REQUIRE(at(g, x0 + 6, z0) != nullptr);
        REQUIRE(at(g, x0 + 6, z0)->def == palisade);
        c.def = gate;
        c.position = {Fixed::from_int(x0 + 6), Fixed::from_int(z0)};
        g.apply(c);
        CHECK(where(g, "core:palisade_gate").size() == 1);
        CHECK(where(g, "core:palisade").size() == 3);
    }

    TEST_CASE("the palisade burns") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 24);
        grant(g, "core:log", 100);
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 4, z0));
        for (int i = 0; i < 400 && where(g, "core:palisade", true).size() < 3; ++i) {
            run(g, 50);
        }
        REQUIRE(where(g, "core:palisade", true).size() == 3);
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
        CHECK(g.fires() == 1);
    }

    TEST_CASE("the trace travels: it is read back as written, bad ones are refused, and two games agree") {
        Game a(core(), map_for(92), setup());
        Game b(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(a, 24);
        const Command wire = trace(a, "core:palisade", x0, z0, x0 + 8, z0 + 8, true);
        BinaryWriter w;
        wire.write(w);
        BinaryReader r(w.bytes());
        Command back;
        REQUIRE(Command::read(r, back));
        CHECK(back == wire);
        // A bend that is neither, or an end off the map, never gets past the reader.
        for (const auto& bad : {+[](Command& c) { c.count = 2; }, +[](Command& c) { c.value = -4; },
                                +[](Command& c) { c.value2 = 1 << 20; }}) {
            Command c = wire;
            bad(c);
            BinaryWriter bw;
            c.write(bw);
            BinaryReader br(bw.bytes());
            Command out;
            CHECK_FALSE(Command::read(br, out));
        }
        // The same orders on two machines: the same game.
        for (Game* g : {&a, &b}) {
            level_up(*g);
            grant(*g, "core:log", 100);
            g->apply(back);
            g->apply(trace(*g, "core:stone_wall", x0 + 12, z0, x0 + 18, z0 + 6));
            run(*g, 600);
        }
        CHECK(a.hash() == b.hash());
        CHECK(where(a, "core:palisade").size() == 5);  // A diagonal: as far on both sides.
        CHECK(where(a, "core:palisade") == where(b, "core:palisade"));
    }

    TEST_CASE("saving and loading keeps the lines, sites and gates as they were") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 24);
        grant(g, "core:log", 100);
        g.apply(trace(g, "core:palisade", x0, z0, x0 + 12, z0));
        run(g, 300);  // Some built, some still sites.
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = building(g, "core:palisade_postern");
        c.position = {Fixed::from_int(x0 + 4), Fixed::from_int(z0)};
        g.apply(c);
        run(g, 50);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(where(loaded, "core:palisade") == where(g, "core:palisade"));
        CHECK(where(loaded, "core:palisade_postern").size() == 1);
        run(g, 400);
        run(loaded, 400);
        CHECK(loaded.hash() == g.hash());
    }

    // Not a test: it writes a saved game to look at the lines in the game itself,
    // since no automatic check sees whether the pieces meet. Run it by name:
    //   salvasprosperia_tests -ts=trace -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_lines.scsave: copy it to the saves folder and load it.
    TEST_CASE("manual: a saved game with lines of every shape" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        const std::filesystem::path file = folder / "manual_lines.scsave";
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        level_up(g);
        grant(g, "core:log", 2000);
        grant(g, "core:stone", 1000);
        for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
            grant(g, food, 3000);
        }
        // Away from the town center: a ring traced where people stroll shuts them in.
        const auto [x0, z0] = open_ground(g, 70, 40);
        const auto lay = [&](const char* def, int ax, int az, int bx, int bz, bool z_first = false) {
            g.apply(trace(g, def, x0 + ax, z0 + az, x0 + bx, z0 + bz, z_first));
        };
        // Until every line laid so far is built (the laborers must reach it: what
        // is inside a ring goes before the ring closes).
        const auto build = [&] {
            for (int i = 0; i < 600; ++i) {
                run(g, 50);
                bool sites = false;
                for (const Building& b : g.buildings().data()) {
                    sites = sites || (b.state == BuildingState::Construction && !g.content().buildings[b.def].line.empty());
                }
                if (!sites) {
                    return;
                }
            }
            for (const Building& b : g.buildings().data()) {
                if (b.state == BuildingState::Construction && !g.content().buildings[b.def].line.empty()) {
                    MESSAGE("never built: " << g.content().buildings[b.def].id << " at (" << b.x - x0 << ", " << b.z - z0 << ")");
                }
            }
        };
        // A wall across where the ring will be, and another that crosses it.
        lay("core:palisade", 0, 12, 24, 12);
        lay("core:palisade", 12, 6, 12, 18);
        // A diagonal, an L along z first, a lone module, and a stone wall.
        lay("core:palisade", 30, 0, 38, 8);
        lay("core:palisade", 30, 14, 38, 20, true);
        lay("core:palisade", 34, 26, 34, 26);
        lay("core:stone_wall", 28, 30, 40, 30);
        build();
        // The ring: an octagon, four straight sides joined by four diagonals.
        lay("core:palisade", 8, 0, 16, 0);
        lay("core:palisade", 16, 0, 24, 8);
        lay("core:palisade", 24, 8, 24, 16);
        lay("core:palisade", 24, 16, 16, 24);
        lay("core:palisade", 16, 24, 8, 24);
        lay("core:palisade", 8, 24, 0, 16);
        lay("core:palisade", 0, 16, 0, 8);
        lay("core:palisade", 0, 8, 8, 0);
        build();
        // A gate in its north side and a postern in its south.
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = building(g, "core:palisade_gate");
        c.position = {Fixed::from_int(x0 + 10), Fixed::from_int(z0)};
        g.apply(c);
        c.def = building(g, "core:palisade_postern");
        c.position = {Fixed::from_int(x0 + 12), Fixed::from_int(z0 + 24)};
        g.apply(c);
        build();
        // Phase 94: a hedge with its arch and a diagonal, a pen of low hedge
        // and one of picket fence with a wall across, each with its gate.
        const auto square = [&](const char* def, int ax, int az, int side) {
            lay(def, ax, az, ax + side, az);
            lay(def, ax + side, az, ax + side, az + side);
            lay(def, ax + side, az + side, ax, az + side);
            lay(def, ax, az + side, ax, az);
        };
        const auto gate = [&](const char* def, int ax, int az) {
            c.def = building(g, def);
            c.position = {Fixed::from_int(x0 + ax), Fixed::from_int(z0 + az)};
            g.apply(c);
        };
        lay("core:picket_fence", 34, 46, 38, 46);  // (Not all the way across: it would shut its builders in.)
        build();
        square("core:hedge", 0, 42, 8);
        lay("core:hedge", 12, 42, 18, 48);
        lay("core:hedge", 18, 48, 18, 50);
        square("core:boxhedge", 20, 42, 6);
        square("core:picket_fence", 30, 42, 8);
        lay("core:picket_fence", 42, 42, 42, 42);
        // Their gates at once: whoever was standing inside must be able to walk out.
        gate("core:hedge_arch", 4, 42);
        gate("core:boxhedge_gate", 22, 42);
        gate("core:picket_gate", 32, 42);
        build();
        // Phase 95: a dirt road with a branch and a crossing, a cobbled street
        // that joins it, and a part of the dirt road made a street.
        lay("core:dirt_road", 0, 60, 40, 60);
        lay("core:dirt_road", 20, 62, 20, 68);
        lay("core:dirt_road", 10, 56, 10, 58);
        lay("core:dirt_road", 10, 62, 10, 66);
        lay("core:dirt_road", 46, 60, 46, 60);
        build();
        lay("core:cobbled_street", 24, 64, 40, 64);
        lay("core:cobbled_street", 40, 62, 40, 62);
        lay("core:cobbled_street", 30, 60, 40, 60);
        build();
        // And a stretch of each left as sites.
        lay("core:cobbled_street", 0, 66, 6, 66);
        lay("core:palisade", 28, 36, 40, 36);
        lay("core:hedge", 0, 54, 6, 54);
        lay("core:boxhedge", 10, 54, 16, 54);
        lay("core:picket_fence", 20, 54, 26, 54);
        run(g, 2);
        save::SaveData data;
        data.header.name = "lines";
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
        REQUIRE(save::write_file(file, data));
        MESSAGE("lines from cell (" << x0 << ", " << z0 << "); town center at (" << g.buildings().get(g.player(0).town_center)->x << ", "
                                    << g.buildings().get(g.player(0).town_center)->z << ")");
    }
}
