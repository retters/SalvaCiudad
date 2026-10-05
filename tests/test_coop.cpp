#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "game/ambient_fauna.h"
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

// The base game with coops that lay clay and whose hens eat coal: things
// nobody else takes, to count them.
std::shared_ptr<const Content> counting() {
    auto c = std::make_shared<Content>(test::core_content());
    const DefIndex clay = c->find_resource("core:clay");
    for (BuildingDef& b : c->buildings) {
        if (b.coop_gives != kNoDef) {
            b.coop_gives = clay;
            b.coop_feed = {c->find_resource("core:coal")};
            b.storage = 200;
        }
    }
    return c;
}

// Room for what is carried to the storage (a new town's center is nearly full).
void storehouse(Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    Command c;
    c.type = CommandType::PlaceBuilding;
    c.def = g.content().find_building("core:storehouse");
    for (std::int32_t dx = 14; dx < 60 && g.can_place(0, c.def, tc->x - dx, tc->z, 0) != PlaceError::None; dx += 2) {
        c.position = {Fixed::from_int(tc->x - dx - 2), Fixed::from_int(tc->z)};
    }
    if (c.position.x == Fixed{}) {
        c.position = {Fixed::from_int(tc->x - 14), Fixed::from_int(tc->z)};
    }
    const std::size_t before = g.buildings().size();
    g.apply(c);
    REQUIRE(g.buildings().size() == before + 1);
    Command done;
    done.type = CommandType::DevBuild;
    g.apply(done);
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

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
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

const Building& at(const Game& g, EntityId id) {
    const Building* b = g.buildings().get(id);
    REQUIRE(b != nullptr);
    return *b;
}

// `n` modules of a line around `b`, a meter from its walls: along its south wall, then its north one.
void fence_around(Game& g, const Building& b, const char* def, std::int32_t n) {
    std::vector<std::pair<std::int32_t, std::int32_t>> spots;
    for (const std::int32_t z : {b.z + b.depth + 1, b.z - 3}) {
        for (std::int32_t x = b.x - 2; x <= b.x + b.width; x += 2) {
            spots.emplace_back(x, z);
        }
    }
    REQUIRE(static_cast<std::size_t>(n) <= spots.size());
    for (std::int32_t i = 0; i < n; ++i) {
        Command c;
        c.type = CommandType::Trace;
        c.def = g.content().find_building(def);
        REQUIRE(c.def != kNoDef);
        c.position = {Fixed::from_int(spots[static_cast<std::size_t>(i)].first), Fixed::from_int(spots[static_cast<std::size_t>(i)].second)};
        c.value = spots[static_cast<std::size_t>(i)].first;
        c.value2 = spots[static_cast<std::size_t>(i)].second;
        g.apply(c);
    }
    build_all(g);
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

std::int32_t in(const Building& b, DefIndex r) {
    std::int32_t n = 0;
    for (const Stock& s : b.stock) {
        n += s.resource == r ? s.amount : 0;
    }
    return n;
}

// The hens the fox took from `coop`, of the events since the last look.
int foxes(Game& g, EntityId coop, int* others = nullptr) {
    int n = 0;
    for (const Game::Event& e : g.take_events()) {
        if (e.kind == Game::Event::Kind::Fox) {
            n += e.entity == coop ? 1 : 0;
            if (others != nullptr) {
                *others += e.entity == coop ? 0 : 1;
            }
        }
    }
    return n;
}

}  // namespace

TEST_SUITE("coop") {
    TEST_CASE("the base game's coop and its guard") {
        const Content& c = test::core_content();
        const BuildingDef& coop = c.buildings[c.find_building("core:decor_chicken_coop")];
        CHECK(coop.coop_gives == c.find_resource("core:eggs"));
        CHECK(coop.coop_hens == 4);
        CHECK(coop.coop_days == 3);
        CHECK(coop.coop_feed_days == 6);
        REQUIRE(coop.coop_feed.size() == 2);
        CHECK(std::count(coop.coop_feed.begin(), coop.coop_feed.end(), c.find_resource("core:wheat")) == 1);
        CHECK(std::count(coop.coop_feed.begin(), coop.coop_feed.end(), c.find_resource("core:barley")) == 1);
        CHECK(coop.workers == 0);
        CHECK(coop.storage >= village::kCoopFeed + 4);
        CHECK(c.buildings[c.find_building("core:decor_kennel")].guard_radius == 12);
        // The hens that are seen around it have their models.
        for (const fauna::Species s : {fauna::Species::Hen, fauna::Species::HenWhite, fauna::Species::Chick}) {
            CHECK(fauna::habit(s) == fauna::Habit::Ground);
            CHECK_FALSE(fauna::model_file(s).empty());
        }
    }

    TEST_CASE("with grain the hens lay, a unit every three days, and without it nothing") {
        Game g(counting(), map_for(92), setup());
        storehouse(g);
        const auto [tx, tz] = town(g);
        const EntityId coop = put(g, "core:decor_chicken_coop", tx + 20, tz - 16);
        REQUIRE(coop.valid());
        REQUIRE(put(g, "core:decor_kennel", at(g, coop).x + 5, at(g, coop).z).valid());  // No fox in this one.
        REQUIRE(g.coop_safe(at(g, coop)));
        CHECK(at(g, coop).flock == 4);
        const DefIndex wheat = g.content().find_resource("core:coal");  // (What these hens eat.)
        REQUIRE(have(g, "core:coal") == 0);
        const std::int32_t had = have(g, "core:clay");
        const std::uint32_t day = g.calendar_day_ticks();
        run(g, 30 * day);
        CHECK(have(g, "core:clay") == had);
        CHECK(at(g, coop).produced == 0);
        // Grain in the storage: a laborer takes some to the coop.
        grant(g, "core:coal", 20);
        bool brought = false;
        for (std::uint32_t t = 0; t < 10 * day && !brought; ++t) {
            g.step();
            brought = in(at(g, coop), wheat) > 0 || at(g, coop).produced > 0;
            CHECK(in(at(g, coop), wheat) <= village::kCoopFeed);
        }
        REQUIRE(brought);
        const std::int32_t before = have(g, "core:clay");
        run(g, 60 * day);
        const std::int32_t laid = have(g, "core:clay") - before;
        const std::int32_t eaten = 20 - have(g, "core:coal");
        MESSAGE("in sixty days: " << laid << " laid, " << eaten << " of grain eaten; in the coop: " << in(at(g, coop), wheat)
                                  << " of grain, feed for " << at(g, coop).produced << " days");
        CHECK(laid >= 19);
        CHECK(laid <= 21);
        CHECK(eaten >= 10);
        CHECK(eaten <= 12);
        CHECK(in(at(g, coop), wheat) <= village::kCoopFeed);
        // The grain is the hens': nobody carries it off, and what was laid is carried to the storage.
        CHECK(have(g, "core:clay") - in(at(g, coop), g.content().find_resource("core:clay")) > 0);
    }

    TEST_CASE("a coop with no fence and no dog loses hens to the fox through a year; with either, none") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        const EntityId bare = put(g, "core:decor_chicken_coop", tx + 24, tz - 30);
        const EntityId fenced = put(g, "core:decor_chicken_coop", tx + 24, tz + 30);
        const EntityId guarded = put(g, "core:decor_chicken_coop", tx - 40, tz - 30);
        REQUIRE(bare.valid());
        REQUIRE(fenced.valid());
        REQUIRE(guarded.valid());
        // Three modules are not a fence; four are, of any line.
        fence_around(g, at(g, fenced), "core:picket_fence", 3);
        CHECK_FALSE(g.coop_safe(at(g, fenced)));
        fence_around(g, at(g, fenced), "core:picket_fence", 4);
        CHECK(g.coop_safe(at(g, fenced)));
        // A kennel within 12 m; one farther is no guard.
        const EntityId far_kennel = put(g, "core:decor_kennel", at(g, guarded).x + 16, at(g, guarded).z);
        REQUIRE(far_kennel.valid());
        CHECK_FALSE(g.coop_safe(at(g, guarded)));
        REQUIRE(put(g, "core:decor_kennel", at(g, guarded).x - 6, at(g, guarded).z).valid());
        CHECK(g.coop_safe(at(g, guarded)));
        CHECK_FALSE(g.coop_safe(at(g, bare)));
        (void)g.take_events();
        int taken = 0;
        int elsewhere = 0;
        // (Not the whole year: where there is no spring the flock is whole again with the new year.)
        for (std::uint32_t t = 0; t < g.year_ticks() - 2 * g.calendar_day_ticks(); t += 50) {
            run(g, 50);
            taken += foxes(g, bare, &elsewhere);
        }
        // (Eight other games lost 1, 3, 2, 2, 2, 3, 4 and 4 in their year; and one coop, through
        // eight years with a spring each, 2, 3, 3, 3, 3, 3, 3 and 4.)
        MESSAGE("the fox took " << taken << " hens; left: " << int(at(g, bare).flock));
        CHECK(taken > 0);
        CHECK(taken <= 4);
        CHECK(at(g, bare).flock == 4 - taken);
        CHECK(elsewhere == 0);
        CHECK(at(g, fenced).flock == 4);
        CHECK(at(g, guarded).flock == 4);
        // A palisade or a hedge keep it out as well.
        const EntityId walled = put(g, "core:decor_chicken_coop", tx - 40, tz + 30);
        REQUIRE(walled.valid());
        fence_around(g, at(g, walled), "core:palisade", 2);
        fence_around(g, at(g, walled), "core:hedge", 4);
        CHECK(g.coop_safe(at(g, walled)));
    }

    TEST_CASE("each hen less is a quarter less laid, and the flock is whole again in spring") {
        GameSetup rules = setup(0b1111);
        rules.rules.climate.minutes = {2, 2, 2, 2};
        Game g(counting(), map_for(92), rules);
        storehouse(g);
        const auto [tx, tz] = town(g);
        const EntityId coop = put(g, "core:decor_chicken_coop", tx + 24, tz - 30);
        REQUIRE(coop.valid());
        grant(g, "core:coal", 60);
        // Until the fox has been, out of spring.
        for (std::uint32_t t = 0; t < 3 * g.year_ticks() && (at(g, coop).flock == 4 || g.calendar().season == Season::Spring); ++t) {
            g.step();
        }
        const int left = at(g, coop).flock;
        REQUIRE(left < 4);
        MESSAGE("hens left: " << left << " in season " << static_cast<int>(g.calendar().season));
        // The spring that follows.
        int most = 0;
        while (g.calendar().season != Season::Spring) {
            g.step();
        }
        for (std::uint32_t t = 0; t < 2 * g.calendar_day_ticks(); ++t) {
            g.step();
            most = std::max<int>(most, at(g, coop).flock);
        }
        CHECK(most == 4);
        // A flock of two lays half: a unit every six days.
        Game half(counting(), map_for(92), setup());
        storehouse(half);
        const EntityId other = put(half, "core:decor_chicken_coop", tx + 24, tz - 30);
        REQUIRE(other.valid());
        grant(half, "core:coal", 60);
        for (std::uint32_t t = 0; t < half.year_ticks() - 3 * half.calendar_day_ticks() && at(half, other).flock > 2; ++t) {
            half.step();
        }
        if (at(half, other).flock == 2) {
            REQUIRE(put(half, "core:decor_kennel", at(half, other).x + 5, at(half, other).z).valid());
            run(half, 12 * half.calendar_day_ticks());  // (Fed by now.)
            const std::int32_t before = have(half, "core:clay");
            run(half, 36 * half.calendar_day_ticks());
            if (at(half, other).flock == 2) {
                CHECK(have(half, "core:clay") - before == 6);
            }
        } else {
            MESSAGE("the fox did not leave two hens in this game: " << int(at(half, other).flock));
        }
    }

    TEST_CASE("saving and loading keeps a coop's hens, its feed and its eggs on the way") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        const EntityId coop = put(g, "core:decor_chicken_coop", tx + 24, tz - 30);
        REQUIRE(coop.valid());
        grant(g, "core:wheat", 30);
        run(g, g.year_ticks() / 3);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(at(loaded, coop).flock == at(g, coop).flock);
        CHECK(at(loaded, coop).produced == at(g, coop).produced);
        CHECK(at(loaded, coop).work_done == at(g, coop).work_done);
        run(g, g.year_ticks() / 3);
        run(loaded, loaded.year_ticks() / 3);
        CHECK(loaded.hash() == g.hash());
        CHECK(at(loaded, coop).flock == at(g, coop).flock);
        CHECK(have(loaded, "core:eggs") == have(g, "core:eggs"));
    }

    // Not a test: a saved game with three coops: one bare, one fenced, one
    // with a kennel beside it; and grain in the storage. Run it by name:
    //   salvaciudad_tests -ts=coop -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_coop.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with coops" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup(0b1111);
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        grant(g, "core:wheat", 40);
        const auto [tx, tz] = town(g);
        const EntityId bare = put(g, "core:decor_chicken_coop", tx + 18, tz - 14);
        const EntityId fenced = put(g, "core:decor_chicken_coop", tx + 30, tz - 14);
        const EntityId guarded = put(g, "core:decor_chicken_coop", tx + 18, tz + 14);
        REQUIRE(bare.valid());
        REQUIRE(fenced.valid());
        REQUIRE(guarded.valid());
        fence_around(g, at(g, fenced), "core:picket_fence", 6);
        REQUIRE(put(g, "core:decor_kennel", at(g, guarded).x + 5, at(g, guarded).z).valid());
        run(g, 900);
        save::SaveData data;
        data.header.name = "coop";
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
        REQUIRE(save::write_file(folder / "manual_coop.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << "); hens: " << int(at(g, bare).flock) << ", " << int(at(g, fenced).flock)
                                   << ", " << int(at(g, guarded).flock));
    }
}
