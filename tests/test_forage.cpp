#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
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
GameSetup setup(std::uint8_t seasons, std::uint8_t rain = 0, Threat diseases = Threat::None) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = seasons;
    s.rules.diseases = diseases;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    s.rules.rain = rain;
    return s;
}
constexpr std::uint8_t kSpring = 0b0001, kSummer = 0b0010, kAutumn = 0b0100, kWinter = 0b1000;

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

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

void finish_all(Game& g) {
    Command c;
    c.type = CommandType::DevBuild;
    g.apply(c);
}

// A building of `def` near (x, z), where it fits; built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = building(g, def);
    for (std::int32_t r = 0; r <= 12; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != r || g.can_place(0, d, x + dx, z + dz, 0) != PlaceError::None) {
                    continue;
                }
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = d;
                c.position = {Fixed::from_int(x + dx), Fixed::from_int(z + dz)};
                g.apply(c);
                finish_all(g);
                for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                    const Building& b = g.buildings().data()[i];
                    if (b.def == d && b.x == x + dx && b.z == z + dz) {
                        return g.buildings().entities()[i];
                    }
                }
            }
        }
    }
    return {};
}

// A feature of the map set down by the developer tools; its index.
std::uint32_t plant(Game& g, FeatureType type, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::DevFeature;
    c.def = static_cast<std::uint16_t>(type);
    c.value = Fixed::one().raw();
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    const std::size_t before = g.map().features.size();
    g.apply(c);
    REQUIRE(g.map().features.size() == before + 1);
    return static_cast<std::uint32_t>(before);
}

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

// A town with a forager at work and, a few steps from it, a tree with a
// hive, a nest, a stump and a ring of mushrooms. Enough to eat, so nobody
// goes hungry (and what the forager brings is eaten too: the tests look
// at what was picked).
struct Camp {
    EntityId forager;
    std::uint32_t hive = 0, nest = 0, stump = 0, ring = 0;
};
Camp camp(Game& g) {
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    const std::int32_t tx = tc->x, tz = tc->z;  // (Building more moves the buildings in memory.)
    Camp c;
    c.forager = put(g, "core:forager", tx + 16, tz);
    REQUIRE(c.forager.valid());
    const Building at = *g.buildings().get(c.forager);
    c.hive = plant(g, FeatureType::BeeTree, at.x + 12, at.z + 2);
    c.nest = plant(g, FeatureType::Nest, at.x + 12, at.z + 8);
    c.stump = plant(g, FeatureType::Stump, at.x - 6, at.z + 2);
    c.ring = plant(g, FeatureType::MushroomRing, at.x + 2, at.z + 12);
    for (int t = 0; t < 400 && g.buildings().get(c.forager)->workers.empty(); ++t) {
        run(g, 10);
    }
    REQUIRE_FALSE(g.buildings().get(c.forager)->workers.empty());
    return c;
}

// What a season's game picks from each in some days, and the most of each
// resource the town had at once.
struct Picked {
    std::int32_t hive = 0, nest = 0, stump = 0, ring = 0;
    std::int32_t honey = 0, eggs = 0, mushrooms = 0;
};
Picked season_of_foraging(std::uint8_t seasons, std::uint8_t rain = 0) {
    const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(seasons, rain));
    Game& g = *g_owned;
    const Camp c = camp(g);
    Picked p;
    const std::uint32_t year = g.calendar().year;
    for (int t = 0; t < 3000 && g.calendar().year == year; ++t) {
        g.step();
        p.honey = std::max(p.honey, have(g, "core:honey"));
        p.eggs = std::max(p.eggs, have(g, "core:eggs"));
        p.mushrooms = std::max(p.mushrooms, have(g, "core:mushrooms"));
        const auto picked = [&](std::uint32_t node) { return g.nodes()[node].fruit_year != 0 ? g.nodes()[node].fruit_picked : 0; };
        p.hive = std::max(p.hive, picked(c.hive));
        p.nest = std::max(p.nest, picked(c.nest));
        p.stump = std::max(p.stump, picked(c.stump));
        p.ring = std::max(p.ring, picked(c.ring));
    }
    return p;
}

// The hash of what generator 7 made: every feature of the kinds there were,
// the starts and the animals' zones.
std::uint64_t old_map_hash(const MapData& m, std::uint32_t& features) {
    BinaryWriter w;
    features = 0;
    for (const MapFeature& f : m.features) {
        if (f.type > FeatureType::StoneDeposit) {
            continue;
        }
        ++features;
        w.u8(static_cast<std::uint8_t>(f.type));
        w.u8(f.species);
        w.u8(f.size);
        w.u16(f.rotation);
        w.i32(f.x.raw());
        w.i32(f.z.raw());
        w.i32(f.scale.raw());
    }
    for (const StartPosition& p : m.starts) {
        w.i32(p.x.raw());
        w.i32(p.z.raw());
    }
    for (const Zone& z : m.zones) {
        if (z.type > ZoneType::Bears) {
            continue;  // (The zones of rabbits and of the lynx came with generator 11, phase 109.)
        }
        w.u8(static_cast<std::uint8_t>(z.type));
        w.i32(z.x.raw());
        w.i32(z.z.raw());
        w.i32(z.radius.raw());
    }
    return fnv1a64(w.bytes());
}

}  // namespace

TEST_SUITE("forage") {
    TEST_CASE("the base game's honey, eggs and mushrooms, where they come from, and who gathers them") {
        const Content& c = test::core_content();
        const auto resource = [&](const char* id) -> const ResourceDef& {
            const DefIndex r = c.find_resource(id);
            REQUIRE(r != kNoDef);
            return c.resources[r];
        };
        for (const char* id : {"core:honey", "core:eggs", "core:mushrooms"}) {
            CAPTURE(id);
            CHECK(resource(id).category == ResourceCategory::Food);
            CHECK(resource(id).nutrition > 0);
            CHECK_FALSE(resource(id).pile.empty());
        }
        // One mushroom in five is a bad one; nothing else is.
        CHECK(resource("core:mushrooms").bad_percent == 20);
        CHECK(resource("core:honey").bad_percent == 0);
        CHECK(resource("core:berries").bad_percent == 0);
        const auto bit = [](Season s) { return static_cast<std::uint8_t>(1u << static_cast<unsigned>(s)); };
        const struct {
            FeatureType type;
            const char* gives;
            Season season;
            bool after_rain;
        } kinds[] = {{FeatureType::BeeTree, "core:honey", Season::Summer, false},
                     {FeatureType::Nest, "core:eggs", Season::Spring, false},
                     {FeatureType::Stump, "core:mushrooms", Season::Autumn, false},
                     {FeatureType::MushroomRing, "core:mushrooms", Season::Autumn, true}};
        const BuildingDef& forager = c.buildings[c.find_building("core:forager")];
        for (const auto& k : kinds) {
            const FeatureDef* fd = c.feature(k.type);
            REQUIRE(fd != nullptr);
            CAPTURE(fd->id);
            CHECK(fd->resource == c.find_resource(k.gives));
            CHECK(fd->seasons == bit(k.season));
            CHECK(fd->after_rain == k.after_rain);
            CHECK(fd->amount >= 4);
            CHECK(fd->regrow_days == 0);
            CHECK_FALSE(fd->models.empty());
            CHECK(((forager.gathers >> static_cast<unsigned>(k.type)) & 1u) != 0);
        }
        // What there was does not give by seasons.
        // (The berry bush does since phase 99.)
        for (const FeatureType old : {FeatureType::Tree, FeatureType::Herbs, FeatureType::StoneDeposit}) {
            REQUIRE(c.feature(old) != nullptr);
            CHECK(c.feature(old)->seasons == 0);
        }
        // The woodcutter does not fell the tree with the hive.
        CHECK(((c.buildings[c.find_building("core:woodcutter")].gathers >> static_cast<unsigned>(FeatureType::BeeTree)) & 1u) == 0);
        // Food poisoning: mild, short, and nobody catches it from anybody.
        const DiseaseDef* poisoning = nullptr;
        for (const DiseaseDef& d : c.diseases) {
            if (d.source == DiseaseSource::Food) {
                poisoning = &d;
            }
        }
        if (poisoning == nullptr) {
            FAIL("no disease from food");
            return;
        }
        CHECK(poisoning->id == "core:poisoning");
        CHECK(poisoning->contagion == 0);
        CHECK(poisoning->chance == 0);
        CHECK(poisoning->days <= 4);
        for (const DiseaseDef& d : c.diseases) {
            if (&d != poisoning) {
                CHECK(d.severity > poisoning->severity);
            }
        }
    }

    TEST_CASE("with the same seed, trees, rocks, starts and zones are where generator 7 put them") {
        const struct {
            std::uint64_t seed;
            MapSize size;
            std::uint8_t players;
            Sea sea;
            std::uint32_t features;
            std::uint64_t hash;
        } golden[] = {{91, MapSize::Small, 1, Sea::None, 2061, 14624677170521850115ull},
                      {92, MapSize::Small, 1, Sea::None, 1049, 4125199294174495172ull},
                      {2026, MapSize::Medium, 4, Sea::None, 7808, 16482399040389084440ull},
                      {7, MapSize::Small, 2, Sea::OneSide, 998, 9029936489130425239ull}};
        for (const auto& want : golden) {
            MapSettings s;
            s.seed = want.seed;
            s.size = want.size;
            s.players = want.players;
            s.sea = want.sea;
            const std::optional<MapData> m = generate_map(s, test::core_content());
            REQUIRE(m.has_value());
            CAPTURE(want.seed);
            CHECK(m->generator_version == worldgen::kGeneratorVersion);
            std::uint32_t features = 0;
            const std::uint64_t hash = old_map_hash(*m, features);
            CHECK(features == want.features);
            CHECK(hash == want.hash);
            // And there is some of each new kind.
            std::map<FeatureType, int> count;
            for (const MapFeature& f : m->features) {
                ++count[f.type];
            }
            for (const FeatureType t : {FeatureType::BeeTree, FeatureType::Nest, FeatureType::Stump}) {
                CHECK(count[t] > 0);
            }
            // Every start has its share a walk away, and none where its town center goes.
            for (const StartPosition& start : m->starts) {
                const auto near = [&](FeatureType t, std::int32_t radius) {
                    int n = 0;
                    for (const MapFeature& f : m->features) {
                        const std::int64_t dx = (f.x - start.x).floor_int(), dz = (f.z - start.z).floor_int();
                        n += f.type == t && dx * dx + dz * dz <= static_cast<std::int64_t>(radius) * radius ? 1 : 0;
                    }
                    return n;
                };
                CHECK(near(FeatureType::BeeTree, worldgen::kStartResourceRadius) >= worldgen::kStartMinBeeTrees);
                CHECK(near(FeatureType::Nest, worldgen::kStartResourceRadius) >= worldgen::kStartMinNests);
                CHECK(near(FeatureType::Stump, worldgen::kStartResourceRadius) >= worldgen::kStartMinMushrooms);
                for (const FeatureType t : {FeatureType::BeeTree, FeatureType::Nest, FeatureType::Stump, FeatureType::MushroomRing}) {
                    CHECK(near(t, 20) == 0);
                }
            }
        }
        // And the same map twice.
        MapSettings s;
        s.seed = 92;
        s.size = MapSize::Small;
        const std::optional<MapData> again = generate_map(s, test::core_content());
        REQUIRE(again.has_value());
        CHECK(again->features == map_for(92).features);
    }

    TEST_CASE("the forager brings eggs in spring, honey in summer and mushrooms in autumn, and none of them out of season") {
        const FeatureDef& hive = *test::core_content().feature(FeatureType::BeeTree);
        const FeatureDef& nest = *test::core_content().feature(FeatureType::Nest);
        const FeatureDef& stump = *test::core_content().feature(FeatureType::Stump);
        const FeatureDef& ring = *test::core_content().feature(FeatureType::MushroomRing);
        const Picked spring = season_of_foraging(kSpring);
        CHECK(spring.nest == nest.amount);
        CHECK(spring.eggs > 0);
        CHECK(spring.hive == 0);
        CHECK(spring.stump == 0);
        CHECK(spring.ring == 0);
        CHECK(spring.honey == 0);
        CHECK(spring.mushrooms == 0);
        const Picked summer = season_of_foraging(kSummer);
        CHECK(summer.hive == hive.amount);
        CHECK(summer.honey > 0);
        CHECK(summer.nest == 0);
        CHECK(summer.stump == 0);
        CHECK(summer.ring == 0);
        CHECK(summer.eggs == 0);
        CHECK(summer.mushrooms == 0);
        const Picked autumn = season_of_foraging(kAutumn);
        CHECK(autumn.stump == stump.amount);
        CHECK(autumn.ring == ring.amount);  // (Without rain in the rules: every ten days, the first of them the first.)
        CHECK(autumn.mushrooms > 0);
        CHECK(autumn.hive == 0);
        CHECK(autumn.nest == 0);
        CHECK(autumn.honey == 0);
        CHECK(autumn.eggs == 0);
        const Picked winter = season_of_foraging(kWinter);
        CHECK(winter.hive + winter.nest + winter.stump + winter.ring == 0);
        CHECK(winter.honey + winter.eggs + winter.mushrooms == 0);
    }

    TEST_CASE("a hive gives its honey once a year: none is left the same year, all of it again the next") {
        const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(kSummer));
        Game& g = *g_owned;
        const Camp c = camp(g);
        const FeatureDef& hive = *g.content().feature(FeatureType::BeeTree);
        CHECK(g.fruit_on(c.hive) == hive.amount);
        const std::uint32_t year = g.calendar().year;
        for (int t = 0; t < 20000 && g.fruit_on(c.hive) > 0; ++t) {
            g.step();
        }
        REQUIRE(g.calendar().year == year);
        CHECK(g.fruit_on(c.hive) == 0);
        CHECK(g.nodes()[c.hive].amount == 1);  // The tree and its hive are still there.
        // The rest of the year: nothing.
        while (g.calendar().year == year) {
            g.step();
            if (g.calendar().year == year) {
                REQUIRE(g.fruit_on(c.hive) == 0);
            }
        }
        // The next: all of it again.
        CHECK(g.fruit_on(c.hive) == hive.amount);
        for (int t = 0; t < 20000 && g.fruit_on(c.hive) > 0; ++t) {
            g.step();
        }
        CHECK(g.fruit_on(c.hive) == 0);
        CHECK(g.nodes()[c.hive].fruit_year == year + 1);
    }

    TEST_CASE("a ring of mushrooms fills the day after it rains, and where it never rains, every ten days") {
        const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(kAutumn, 200));
        Game& g = *g_owned;
        const Camp c = camp(g);
        const FeatureDef& ring = *g.content().feature(FeatureType::MushroomRing);
        const std::uint32_t day = g.calendar_day_ticks();
        // From the first tick of a day on, day by day.
        while (g.tick() % day != 0) {
            g.step();
        }
        int filled = 0, emptied = 0;
        std::uint32_t last_cycle = g.ring_cycle();
        for (int d = 0; d < 60; ++d) {
            const std::uint64_t today = g.calendar_day();
            // The last day that came after a day of rain, counted from today.
            std::uint32_t want = 0;
            for (std::uint64_t back = today; want == 0; --back) {
                if (back > 0 && g.rained(back - 1)) {
                    want = static_cast<std::uint32_t>(back) + 1;
                }
                if (back == 0) {
                    break;
                }
            }
            CHECK(g.ring_cycle() == want);
            if (g.ring_cycle() != last_cycle) {
                // Just filled: all of it is there, whatever was left.
                CHECK(g.fruit_on(c.ring) == ring.amount);
                ++filled;
                last_cycle = g.ring_cycle();
            }
            if (g.ring_cycle() == 0) {
                CHECK(g.fruit_on(c.ring) == 0);
            }
            const std::int32_t before = g.fruit_on(c.ring);
            run(g, day);
            emptied += before > 0 && g.calendar_day() == today + 1 && g.ring_cycle() == last_cycle && g.fruit_on(c.ring) == 0 ? 1 : 0;
        }
        MESSAGE("in 60 days of autumn the ring filled " << filled << " times and was picked clean " << emptied << " times");
        CHECK(filled >= 5);
        CHECK(emptied >= 1);  // (The forager has the bushes of autumn to pick too.)
        // Where it never rains: the days that are a multiple of ten.
        const auto dry_owned = std::make_unique<Game>(core(), map_for(92), setup(kAutumn, 0));
        Game& dry = *dry_owned;
        for (int d = 0; d < 35; ++d) {
            CHECK(dry.ring_cycle() == static_cast<std::uint32_t>(d / 10 * 10) + 1);
            run(dry, dry.calendar_day_ticks());
        }
        // And out of autumn, never.
        const auto summer_owned = std::make_unique<Game>(core(), map_for(92), setup(kSummer, 200));
        Game& summer = *summer_owned;
        for (int d = 0; d < 30; ++d) {
            CHECK(summer.ring_cycle() == 0);
            run(summer, summer.calendar_day_ticks());
        }
    }

    TEST_CASE("without a healer some who eat mushrooms are poisoned; with one, or without diseases, nobody is") {
        // A town with plenty of mushrooms to eat, for a while. How many fell ill of it.
        const auto poisoned = [](Threat diseases, bool healer) {
            const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(kSummer, 0, diseases));
            Game& g = *g_owned;
            const Building* tc = g.buildings().get(g.player(0).town_center);
            REQUIRE(tc != nullptr);
            const std::int32_t tx = tc->x, tz = tc->z;
            // Mushrooms beside what it started with: they are eaten in turn with the rest.
            grant(g, "core:mushrooms", 4000);
            if (healer) {
                REQUIRE(put(g, "core:healer", tx + 16, tz).valid());
                CHECK(g.has_healer(0));
            } else {
                CHECK_FALSE(g.has_healer(0));
            }
            DefIndex poisoning = kNoDef;
            for (std::size_t d = 0; d < g.content().diseases.size(); ++d) {
                if (g.content().diseases[d].source == DiseaseSource::Food) {
                    poisoning = static_cast<DefIndex>(d);
                }
            }
            REQUIRE(poisoning != kNoDef);
            std::map<std::uint32_t, bool> fell;
            const std::int32_t before = have(g, "core:mushrooms");
            // (A villager eats every thirty days or so: several meals each.)
            for (int t = 0; t < 14000; ++t) {
                g.step();
                for (std::size_t i = 0; i < g.villagers().size(); ++i) {
                    if (g.villagers().data()[i].disease == poisoning + 1) {
                        fell[g.villagers().entities()[i].index] = true;
                    }
                }
            }
            REQUIRE(have(g, "core:mushrooms") < before - 20);  // They did eat them.
            return static_cast<int>(fell.size());
        };
        const int without = poisoned(Threat::Medium, false);
        const int with_healer = poisoned(Threat::Medium, true);
        const int no_diseases = poisoned(Threat::None, false);
        MESSAGE("poisoned: " << without << " without a healer, " << with_healer << " with one, " << no_diseases
                             << " in a game without diseases");
        CHECK(without > 0);
        CHECK(with_healer == 0);
        CHECK(no_diseases == 0);
    }

    TEST_CASE("saving and loading keeps what was picked and when the rings filled") {
        const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(kAutumn, 200));
        Game& g = *g_owned;
        const Camp c = camp(g);
        for (int t = 0; t < 20000 && !(g.ring_cycle() != 0 && g.nodes()[c.stump].fruit_picked >= 2); ++t) {
            g.step();
        }
        REQUIRE(g.ring_cycle() != 0);
        BinaryWriter w;
        g.save(w);
        const auto loaded_owned = std::make_unique<Game>(core(), map_for(92), setup(kSpring));
        Game& loaded = *loaded_owned;
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.ring_cycle() == g.ring_cycle());
        for (const std::uint32_t node : {c.hive, c.nest, c.stump, c.ring}) {
            CHECK(loaded.fruit_on(node) == g.fruit_on(node));
            CHECK(loaded.nodes()[node].fruit_picked == g.nodes()[node].fruit_picked);
        }
        run(g, 900);
        run(loaded, 900);
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.ring_cycle() == g.ring_cycle());
        CHECK(loaded.fruit_on(c.ring) == g.fruit_on(c.ring));
    }

    TEST_CASE("building over a nest takes it away for good") {
        const auto g_owned = std::make_unique<Game>(core(), map_for(92), setup(kSpring));
        Game& g = *g_owned;
        const Camp c = camp(g);
        const MapFeature nest = g.map().features[c.nest];
        REQUIRE(g.fruit_on(c.nest) > 0);
        REQUIRE(put(g, "core:palisade", nest.x.floor_int() - 1, nest.z.floor_int() - 1).valid());
        CHECK(g.nodes()[c.nest].amount == 0);
        CHECK(g.fruit_on(c.nest) == 0);
    }

    // Not a test: a saved game in autumn, the day after rain, with a forager
    // and a tree with a hive, nests, stumps and rings of mushrooms around it,
    // and honey, eggs and mushrooms in the town's stores. Run it by name:
    //   salvasprosperia_tests -ts=forage -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_forage.scsave: copy it to the saves folder and load it.
    TEST_CASE("manual: a saved game with hives, nests, stumps and mushrooms" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        const std::filesystem::path file = folder / "manual_forage.scsave";
        GameSetup rules = setup(kAutumn, 200);
        rules.rules.climate.minutes = {0, 0, 30, 0};  // Long days, to have time to look (and only autumn has any).
        rules.rules.fog = FogMode::None;
        const auto g_owned = std::make_unique<Game>(core(), map_for(92), rules);
        Game& g = *g_owned;
        const Camp c = camp(g);
        const Building at = *g.buildings().get(c.forager);
        // More of each, in a row south of the forager, to compare their looks.
        for (int k = 0; k < 3; ++k) {
            (void)plant(g, FeatureType::BeeTree, at.x - 8 + 6 * k, at.z + 18);
            (void)plant(g, FeatureType::Nest, at.x - 8 + 6 * k, at.z + 22);
            (void)plant(g, FeatureType::Stump, at.x - 8 + 6 * k, at.z + 26);
            (void)plant(g, FeatureType::MushroomRing, at.x - 8 + 6 * k, at.z + 30);
        }
        const Building* tc = g.buildings().get(g.player(0).town_center);
        const std::int32_t tx = tc->x, tz = tc->z;
        REQUIRE(put(g, "core:storehouse", tx - 16, tz).valid());
        grant(g, "core:honey", 60);
        grant(g, "core:eggs", 60);
        grant(g, "core:mushrooms", 60);
        // The first tick of a day when the rings have just filled.
        for (int t = 0; t < 200000 && !(g.ring_cycle() == g.calendar_day() + 1 && g.tick() % g.calendar_day_ticks() == 5); ++t) {
            g.step();
        }
        REQUIRE(g.ring_cycle() != 0);
        save::SaveData data;
        data.header.name = "forage";
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
        MESSAGE("forager at (" << at.x << ", " << at.z << "); town center at (" << tx << ", " << tz << "); raining " << g.raining());
    }
}
