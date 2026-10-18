#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <tuple>
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

// A small map with the sea on one side whose start is neither by the sea
// nor far from it: between 200 and 420 m. (The first seed that gives one.)
const MapData& coast_map() {
    static std::optional<MapData> map;
    for (std::uint64_t seed = 1; seed < 40 && !map; ++seed) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.sea = Sea::OneSide;
        std::optional<MapData> m = generate_map(s, test::core_content());
        REQUIRE(m.has_value());
        const auto probe_owned = std::make_unique<Game>(std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &test::core_content()), *m, GameSetup{});
        Game& probe = *probe_owned;
        const std::int32_t sx = m->starts[0].x.floor_int(), sz = m->starts[0].z.floor_int();
        std::int64_t nearest = INT64_MAX;
        for (std::int32_t z = 0; z < m->size; z += 4) {
            for (std::int32_t x = 0; x < m->size; x += 4) {
                if (probe.sea_at(x, z)) {
                    nearest = std::min<std::int64_t>(nearest, static_cast<std::int64_t>(x - sx) * (x - sx) + static_cast<std::int64_t>(z - sz) * (z - sz));
                }
            }
        }
        if (nearest >= 200 * 200 && nearest <= 420 * 420) {
            MESSAGE("coast map: seed " << seed << ", the sea " << std::sqrt(static_cast<double>(nearest)) << " m from the start");
            map = std::move(*m);
        }
    }
    REQUIRE(map.has_value());
    return *map;
}

// A small map without sea.
const MapData& inland_map() {
    static std::optional<MapData> map;
    if (!map) {
        MapSettings s;
        s.seed = 92;
        s.size = MapSize::Small;
        s.sea = Sea::None;
        map = generate_map(s, test::core_content());
        REQUIRE(map.has_value());
    }
    return *map;
}

std::uint8_t race(const char* id) {
    const Content& c = test::core_content();
    for (std::size_t i = 0; i < c.races.size(); ++i) {
        if (c.races[i].id == id) {
            return static_cast<std::uint8_t>(i);
        }
    }
    FAIL("no race " << id);
    return 0;
}

// A town of humans, and nobody else comes.
GameSetup setup(std::uint64_t seed = 15) {
    GameSetup s;
    s.seed = seed;
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    s.rules.races.fill(race("core:human"));
    s.rules.other_races = 0;
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

// A town that lacks nothing, with a storehouse; where its center is.
std::pair<std::int32_t, std::int32_t> town(Game& g) {
    grant(g, "core:bread", 6000);
    grant(g, "core:firewood", 3000);
    const Building tc = at(g, g.player(0).town_center);  // (A copy: building moves the others.)
    REQUIRE(put(g, "core:storehouse", tc.x - 26, tc.z).valid());
    return {tc.x + tc.width / 2, tc.z + tc.depth / 2};
}

// Food and firewood for another month.
void supply(Game& g) {
    grant(g, "core:bread", std::max(0, 6000 - have(g, "core:bread")));
    grant(g, "core:firewood", std::max(0, 3000 - have(g, "core:firewood")));
}

std::uint32_t today(const Game& g) {
    return static_cast<std::uint32_t>(g.calendar_day());
}

// The town's question, if it has one waiting; or the place it protects.
const Happening* turtles(const Game& g, HappeningState state = HappeningState::Asked) {
    for (const Happening& h : g.happenings()) {
        if (h.kind == HappeningKind::Turtles && h.state == state) {
            return &h;
        }
    }
    return nullptr;
}

void answer(Game& g, std::int32_t which) {
    Command c;
    c.type = CommandType::AnswerHappening;
    c.def = static_cast<std::uint16_t>(HappeningKind::Turtles);
    c.value = which;
    g.apply(c);
}

// Runs until the town is asked (a year at most), keeping it supplied. Whether it was.
bool until_asked(Game& g, std::uint32_t most_ticks = 0) {
    const std::uint32_t most = most_ticks != 0 ? most_ticks : g.year_ticks();
    for (std::uint32_t t = 0; t < most && turtles(g) == nullptr; ++t) {
        if (g.tick() % g.calendar_month_ticks() == 0) {
            supply(g);
        }
        g.step();
    }
    return turtles(g) != nullptr;
}

void run_days(Game& g, std::uint32_t days) {
    const std::uint32_t until = today(g) + days;
    while (today(g) < until) {
        if (g.tick() % g.calendar_month_ticks() == 0) {
            supply(g);
        }
        g.step();
    }
}

// Loose stones at (x, z).
std::uint32_t stones(Game& g, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::DevFeature;
    c.def = static_cast<std::uint16_t>(FeatureType::LooseStones);
    c.value = Fixed::one().raw();
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    const std::size_t before = g.map().features.size();
    g.apply(c);
    REQUIRE(g.map().features.size() == before + 1);
    return static_cast<std::uint32_t>(before);
}

std::int64_t square(std::int64_t v) {
    return v * v;
}

}  // namespace

TEST_SUITE("turtles") {
    TEST_CASE("one day of every summer the turtles come out to a free beach near the town, and the town is asked") {
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        (void)g.take_events();
        const std::optional<FixedVec2> beach = g.turtle_beach(0);
        REQUIRE(beach.has_value());
        const std::uint32_t day = g.happening_day(HappeningKind::Turtles, 0, 0);
        const std::uint64_t noon = (static_cast<std::uint64_t>(day)) * g.calendar_day_ticks() + g.calendar_day_ticks() / 2;
        CHECK(sim::calendar(g.rules().climate, noon).season == Season::Summer);
        REQUIRE(until_asked(g));
        CHECK(today(g) == day);
        CHECK(g.calendar().season == Season::Summer);
        const Happening h = *turtles(g);
        CHECK(h.town == 0);
        CHECK(h.count == village::kTurtlesFirst);
        CHECK(h.until_day == day + village::kAnswerDays);
        CHECK(h.at == *beach);
        // Sand by the sea, within reach of the town, with nothing built by it.
        const std::int32_t x = h.at.x.floor_int(), z = h.at.z.floor_int();
        CHECK(g.map().terrain_at(x, z) == Terrain::Sand);
        CHECK_FALSE(g.map().water_at(x, z));
        CHECK((g.sea_at(x - 8, z) || g.sea_at(x + 8, z) || g.sea_at(x, z - 8) || g.sea_at(x, z + 8)));
        CHECK(square(x - tx) + square(z - tz) <= square(village::kTurtleReach));
        for (const Building& b : g.buildings().data()) {
            CHECK(square(b.x + b.width / 2 - x) + square(b.z + b.depth / 2 - z) > square(village::kBeachMeters));
        }
        int notices = 0;
        for (const Game::Event& e : g.take_events()) {
            if (e.kind == Game::Event::Kind::Turtles) {
                ++notices;
                CHECK(e.owner == 0);
                CHECK(e.at == h.at);
                CHECK(e.value == village::kTurtlesFirst);
            }
        }
        CHECK(notices == 1);
        // Nothing is protected yet: the town may still build there.
        CHECK_FALSE(g.protected_ground(x, z, 1, 1));
        CHECK(g.town_mood(0) == 0);
    }

    TEST_CASE("without an answer in three days nothing happens, and they come again the next year") {
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        (void)town(g);
        REQUIRE(until_asked(g));
        const std::uint32_t day = today(g);
        const std::int32_t eggs = have(g, "core:eggs");
        (void)g.take_events();
        for (std::uint32_t d = 0; d < village::kAnswerDays; ++d) {
            CHECK(turtles(g) != nullptr);
            run_days(g, 1);
        }
        CHECK(today(g) == day + village::kAnswerDays);
        CHECK(g.happenings().empty());
        CHECK(g.town_mood(0) == 0);
        CHECK(have(g, "core:eggs") == eggs);
        CHECK(g.player(0).turtles == 0);
        CHECK_FALSE(g.player(0).turtles_gone);
        // An answer now is too late.
        const std::uint32_t rejected = g.rejected_commands();
        answer(g, 1);
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(g.happenings().empty());
        // The next summer: again, as many as the first time.
        run_days(g, 40);
        REQUIRE(until_asked(g));
        CHECK(today(g) / kDaysPerYear == 1);
        CHECK(turtles(g)->count == village::kTurtlesFirst);
    }

    TEST_CASE("protecting the beach: nobody builds there for ten days, the town is in a good mood, and more come every year") {
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        (void)town(g);
        REQUIRE(until_asked(g));
        const Happening asked = *turtles(g);
        const std::int32_t x = asked.at.x.floor_int(), z = asked.at.z.floor_int();
        const DefIndex house = g.content().find_building("core:house");
        // Before the answer the ground is as ever; land 50 m inland of the place, for later.
        std::pair<std::int32_t, std::int32_t> inland{0, 0};
        bool found = false;
        for (std::int32_t r = 45; r <= 70 && !found; r += 5) {
            for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{-r, 0}, std::pair{0, r}, std::pair{0, -r}}) {
                if (!found && g.can_place(0, house, x + dx, z + dz, 0) == PlaceError::None) {
                    inland = {x + dx, z + dz};
                    found = true;
                }
            }
        }
        REQUIRE(found);
        const PlaceError there = g.can_place(0, house, x - 2, z - 2, 0);
        CHECK(there != PlaceError::Protected);
        (void)g.take_events();
        answer(g, 1);
        const std::uint32_t day = today(g);
        REQUIRE(turtles(g) == nullptr);
        const Happening* kept = turtles(g, HappeningState::Protected);
        REQUIRE(kept != nullptr);
        CHECK(kept->at == asked.at);
        CHECK(kept->until_day == day + village::kProtectDays);
        CHECK(g.town_mood(0) == village::kMoodPoints);
        CHECK(g.player(0).turtles == village::kTurtlesFirst + 1);
        int notices = 0;
        for (const Game::Event& e : g.take_events()) {
            notices += e.kind == Game::Event::Kind::TurtlesKept ? 1 : 0;
        }
        CHECK(notices == 1);
        // A second answer is refused: it was given.
        const std::uint32_t rejected = g.rejected_commands();
        answer(g, 2);
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK_FALSE(g.player(0).turtles_gone);
        // The ten days: nothing is built within 30 m of the place, and farther it is as ever.
        for (std::uint32_t d = 0; d < village::kProtectDays; ++d) {
            CHECK(g.can_place(0, house, x - 2, z - 2, 0) == PlaceError::Protected);
            CHECK(g.protected_ground(x + village::kBeachMeters, z, 1, 1));
            CHECK_FALSE(g.protected_ground(x + village::kBeachMeters + 1, z, 1, 1));
            CHECK(g.can_place(0, house, inland.first, inland.second, 0) == PlaceError::None);
            run_days(g, 1);
        }
        CHECK(turtles(g, HappeningState::Protected) == nullptr);
        CHECK(g.can_place(0, house, x - 2, z - 2, 0) == there);
        CHECK(g.town_mood(0) == 0);
        // Year after year: one more each time, up to six.
        std::uint8_t last = village::kTurtlesFirst;
        for (std::uint32_t year = 1; year <= 5; ++year) {
            run_days(g, 30);
            REQUIRE(until_asked(g));
            CHECK(today(g) / kDaysPerYear == year);
            const std::uint8_t came = turtles(g)->count;
            CHECK(came == std::min<std::uint8_t>(village::kTurtlesMost, static_cast<std::uint8_t>(last + 1)));
            last = came;
            answer(g, 1);
        }
        CHECK(last == village::kTurtlesMost);
    }

    TEST_CASE("while the beach is protected nobody gathers there") {
        // Two towns alike on a coast with no stone but what is put on the beach: one protects it, the other
        // lets the days go by. How many ticks after the turtles came a stonecutter sets out for a stone of
        // the beach (the town is far: getting there and back is another matter).
        const auto first_taken = [](bool protect) {
            MapData bare = coast_map();
            std::erase_if(bare.features, [](const MapFeature& f) {
                return f.type == FeatureType::Stone || f.type == FeatureType::StoneDeposit || f.type == FeatureType::LooseStones;
            });
            const auto g_owned = std::make_unique<Game>(core(), bare, setup());
            Game& g = *g_owned;
            (void)town(g);
            // A stonecutter 45 m inland of where they will come out, from the first day: its people are there by then.
            const std::optional<FixedVec2> beach = g.turtle_beach(0);
            REQUIRE(beach.has_value());
            const std::int32_t x = beach->x.floor_int(), z = beach->z.floor_int();
            const Building tc = at(g, g.player(0).town_center);
            const double len = std::sqrt(static_cast<double>(square(tc.x - x) + square(tc.z - z)));
            const EntityId cutter = put(g, "core:stonecutter", static_cast<std::int32_t>(x + (tc.x - x) * 45.0 / len),
                                        static_cast<std::int32_t>(z + (tc.z - z) * 45.0 / len));
            REQUIRE(cutter.valid());
            REQUIRE(square(at(g, cutter).x - x) + square(at(g, cutter).z - z) > square(village::kBeachMeters + 6));
            REQUIRE(until_asked(g));
            REQUIRE(turtles(g)->at == *beach);
            REQUIRE(at(g, cutter).workers.size() == 2);
            std::vector<std::uint32_t> on_beach;
            for (int n = 0; n < 4; ++n) {
                const std::int32_t bx = x + (n % 2) * 3 - 1, bz = z + (n / 2) * 3 - 1;
                if (!g.map().water_at(bx, bz)) {
                    on_beach.push_back(stones(g, bx, bz));
                }
            }
            REQUIRE(on_beach.size() >= 2);
            // Somebody is on the way to one, or at it.
            const auto wanted = [&] {
                bool any = false;
                for (const std::uint32_t i : on_beach) {
                    any = any || g.nodes()[i].reserved != 0;
                }
                return any;
            };
            if (protect) {
                answer(g, 1);
                REQUIRE(turtles(g, HappeningState::Protected) != nullptr);
            }
            std::uint32_t t = 0;
            for (; t < 8000 && !wanted(); ++t) {
                if (g.tick() % g.calendar_month_ticks() == 0) {
                    supply(g);
                }
                g.step();
                // While the beach is protected, nobody; and the hut has nothing to take.
                if (turtles(g, HappeningState::Protected) != nullptr) {
                    CHECK_FALSE(wanted());
                }
            }
            CHECK(wanted());
            return t;
        };
        const std::uint32_t free_beach = first_taken(false);
        const std::uint32_t kept_beach = first_taken(true);
        const std::uint32_t day = 100;  // (Ticks of a day of the calendar, in these games.)
        MESSAGE("a stonecutter sets out for the beach: after " << free_beach << " ticks with nobody protecting it, after " << kept_beach
                                                              << " when it is protected");
        // Left alone, within the ten days; protected, only when they are over.
        CHECK(free_beach < village::kProtectDays * day - day);
        CHECK(kept_beach >= village::kProtectDays * day - day);
    }

    TEST_CASE("taking the eggs: the town has them at once, and the turtles never come back") {
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const EntityId forager = put(g, "core:forager", tx + 22, tz + 12);
        REQUIRE(forager.valid());
        REQUIRE(until_asked(g));
        const Happening asked = *turtles(g);
        const std::int32_t eggs = have(g, "core:eggs");
        const DefIndex egg = g.content().find_resource("core:eggs");
        std::int32_t in_hut = 0;
        for (const Stock& s : at(g, forager).stock) {
            in_hut += s.resource == egg ? s.amount : 0;
        }
        (void)g.take_events();
        answer(g, 2);
        CHECK(g.happenings().empty());
        CHECK(have(g, "core:eggs") == eggs + asked.count * village::kTurtleEggs);
        std::int32_t now_in_hut = 0;
        for (const Stock& s : at(g, forager).stock) {
            now_in_hut += s.resource == egg ? s.amount : 0;
        }
        CHECK(now_in_hut == in_hut + asked.count * village::kTurtleEggs);  // To the gatherers' hut.
        CHECK(g.player(0).turtles_gone);
        CHECK(g.town_mood(0) == 0);
        CHECK_FALSE(g.protected_ground(asked.at.x.floor_int(), asked.at.z.floor_int(), 1, 1));
        int notices = 0;
        for (const Game::Event& e : g.take_events()) {
            if (e.kind == Game::Event::Kind::TurtlesTaken) {
                ++notices;
                CHECK(e.value == asked.count * village::kTurtleEggs);
            }
        }
        CHECK(notices == 1);
        // Three more years: never again.
        CHECK_FALSE(until_asked(g, 3 * g.year_ticks()));
        CHECK(g.happenings().empty());
        // Without a hut of gatherers the eggs go to the town itself.
        const auto plain_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& plain = *plain_owned;
        (void)town(plain);
        REQUIRE(until_asked(plain));
        const std::int32_t before = have(plain, "core:eggs");
        answer(plain, 2);
        CHECK(have(plain, "core:eggs") == before + village::kTurtlesFirst * village::kTurtleEggs);
    }

    TEST_CASE("no turtles on a map without sea, on a beach the town has not explored, or by a building") {
        const auto dry_owned = std::make_unique<Game>(core(), inland_map(), setup());
        Game& dry = *dry_owned;
        (void)town(dry);
        CHECK_FALSE(dry.turtle_beach(0).has_value());
        CHECK_FALSE(until_asked(dry, 2 * dry.year_ticks()));
        // The same coast under the fog of war: the town has not been to the sea.
        GameSetup foggy = setup();
        foggy.rules.fog = FogMode::Static;
        const auto fog_owned = std::make_unique<Game>(core(), coast_map(), foggy);
        Game& fog = *fog_owned;
        (void)town(fog);
        CHECK_FALSE(fog.turtle_beach(0).has_value());
        CHECK_FALSE(until_asked(fog));
        // A building on last year's beach: this year they come out somewhere else, or not at all.
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        (void)town(g);
        REQUIRE(until_asked(g));
        const FixedVec2 first = turtles(g)->at;
        run_days(g, village::kAnswerDays + 1);
        const EntityId house = put(g, "core:storehouse", first.x.floor_int() - 2, first.z.floor_int() - 2);
        REQUIRE(house.valid());
        const std::optional<FixedVec2> next = g.turtle_beach(0);
        if (next) {
            CHECK(*next != first);
            const Building b = at(g, house);
            const std::int64_t nx = next->x.floor_int(), nz = next->z.floor_int();
            const std::int64_t dx = nx < b.x ? b.x - nx : nx > b.x + b.width - 1 ? nx - (b.x + b.width - 1) : 0;
            const std::int64_t dz = nz < b.z ? b.z - nz : nz > b.z + b.depth - 1 ? nz - (b.z + b.depth - 1) : 0;
            CHECK(dx * dx + dz * dz > square(village::kBeachMeters));
        }
    }

    TEST_CASE("in a game with nights the turtles come out at night, in summer") {
        GameSetup rules = setup();
        rules.rules.day_night.day = 3;
        rules.rules.day_night.night = 2;
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), rules);
        Game& g = *g_owned;
        (void)town(g);
        REQUIRE(until_asked(g));
        CHECK(g.night());
        CHECK(g.calendar().season == Season::Summer);
        CHECK(today(g) >= g.happening_day(HappeningKind::Turtles, 0, 0));
    }

    TEST_CASE("saving and loading keeps the question waiting, the protected beach and what the town did") {
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& g = *g_owned;
        (void)town(g);
        REQUIRE(until_asked(g));
        BinaryWriter w;
        g.save(w);
        const auto loaded_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& loaded = *loaded_owned;
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.happenings() == g.happenings());
        REQUIRE(turtles(loaded) != nullptr);
        // The answer does the same in both.
        answer(g, 1);
        answer(loaded, 1);
        run(g, 4 * g.calendar_day_ticks());
        run(loaded, 4 * loaded.calendar_day_ticks());
        CHECK(loaded.hash() == g.hash());
        REQUIRE(turtles(g, HappeningState::Protected) != nullptr);
        BinaryWriter w2;
        g.save(w2);
        const auto again_owned = std::make_unique<Game>(core(), coast_map(), setup());
        Game& again = *again_owned;
        BinaryReader r2(w2.bytes());
        REQUIRE(again.load(r2, core()));
        CHECK(again.hash() == g.hash());
        const Happening kept = *turtles(again, HappeningState::Protected);
        CHECK(again.protected_ground(kept.at.x.floor_int(), kept.at.z.floor_int(), 1, 1));
        CHECK(again.player(0).turtles == village::kTurtlesFirst + 1);
        CHECK(again.player(0).turtle_year == 1);
        CHECK(again.town_mood(0) == g.town_mood(0));
    }

    // Not a test: a saved game the night the turtles come out, with the question waiting.
    //   salvasprosperia_tests -ts=turtles -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_turtles.scsave: copy it to the saves folder and load it.
    TEST_CASE("manual: a saved game with the turtles on the beach and the question waiting" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        const auto g_owned = std::make_unique<Game>(core(), coast_map(), rules);
        Game& g = *g_owned;
        (void)town(g);
        // (So that they are six: five years protected.)
        for (int year = 0; year < 3; ++year) {
            REQUIRE(until_asked(g));
            answer(g, 1);
            run_days(g, 30);
        }
        REQUIRE(until_asked(g));
        save::SaveData data;
        data.header.name = "turtles";
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
        REQUIRE(save::write_file(folder / "manual_turtles.scsave", data));
        MESSAGE(static_cast<int>(turtles(g)->count) << " turtles at (" << turtles(g)->at.x.floor_int() << ", " << turtles(g)->at.z.floor_int()
                                                    << "), map of " << g.map().size);
    }
}
