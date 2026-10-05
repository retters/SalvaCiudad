#include <doctest.h>

#include <algorithm>
#include <bit>
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

// Summer, with the beasts as ever (those the tests put) and nothing else to fear.
GameSetup setup() {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = 0b0010;
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::Medium;
    s.rules.other_races = 0;
    return s;
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

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

// Until just after the homes were looked at again (once a day).
void days(Game& g, int n) {
    for (int i = 0; i < n; ++i) {
        do {
            g.step();
        } while (g.tick() % g.day_ticks() != 0);
    }
    run(g, 2);
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

FixedVec2 middle(const Building& b) {
    return {Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2), Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2)};
}

// A beast put on the map `dx`, `dz` meters from the middle of `b`. Its id.
EntityId beast(Game& g, CreatureKind kind, const Building& b, std::int32_t dx, std::int32_t dz) {
    Command c;
    c.type = CommandType::DevBeast;
    c.def = static_cast<DefIndex>(kind);
    c.position = {Fixed::from_int(b.x + b.width / 2 + dx), Fixed::from_int(b.z + b.depth / 2 + dz)};
    const std::size_t before = g.creatures().size();
    const std::uint32_t rejected = g.rejected_commands();
    g.apply(c);
    REQUIRE(g.rejected_commands() == rejected);
    REQUIRE(g.creatures().size() == before + 1);
    return g.creatures().entities()[before];
}

struct Seen {
    int barks = 0;
    int attacks = 0;
    std::uint16_t barked_at = 0xFFFF;
};
void look(Game& g, Seen& s) {
    for (const Game::Event& e : g.take_events()) {
        if (e.kind == Game::Event::Kind::Barked) {
            ++s.barks;
            s.barked_at = e.value;
        }
        s.attacks += e.kind == Game::Event::Kind::Attacked ? 1 : 0;
    }
}

// A town with a kennel by its center (or without), and a wolf put 10 m north of where the kennel goes.
struct Scene {
    EntityId kennel;
    Building spot;  // Where the kennel is (or would be).
};
Scene scene(Game& g, bool with_kennel) {
    const auto [tx, tz] = town(g);
    Scene s;
    if (with_kennel) {
        s.kennel = put(g, "core:decor_kennel", tx + 3, tz - 5);
        REQUIRE(s.kennel.valid());
        s.spot = at(g, s.kennel);
    } else {
        Game probe(core(), map_for(92), setup());
        const EntityId k = put(probe, "core:decor_kennel", tx + 3, tz - 5);
        REQUIRE(k.valid());
        s.spot = at(probe, k);
    }
    (void)g.take_events();
    return s;
}

int fleeing_near(const Game& g, const Building& kennel, std::int32_t radius) {
    int n = 0;
    for (const Villager& v : g.villagers().data()) {
        const std::int64_t dx = v.position.x.floor_int() - (kennel.x + kennel.width / 2);
        const std::int64_t dz = v.position.z.floor_int() - (kennel.z + kennel.depth / 2);
        n += v.task == Task::Flee && dx * dx + dz * dz <= static_cast<std::int64_t>(radius + 3) * (radius + 3) ? 1 : 0;
    }
    return n;
}

int cats(const Game& g) {
    int n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.cat != 0 ? 1 : 0;
    }
    return n;
}

std::int32_t food(const Game& g) {
    std::int32_t n = 0;
    const auto stored = g.stored(0);
    for (std::size_t r = 0; r < stored.size(); ++r) {
        n += g.content().resources[r].category == ResourceCategory::Food ? stored[r] : 0;
    }
    return n;
}

// What a house's happiness has over its base, its needs met and its neighborhood.
std::int32_t extra(const Building& b) {
    return b.happiness - (28 + 8 * std::popcount(static_cast<unsigned>(b.needs)) + std::clamp(b.desirability / 2, -10, 10));
}

}  // namespace

TEST_SUITE("pets") {
    TEST_CASE("the base game's kennel, the people who like cats, and the dogs and cats that are seen") {
        const Content& c = test::core_content();
        CHECK(c.buildings[c.find_building("core:decor_kennel")].guard_radius == 12);
        int like = 0;
        for (const RaceDef& r : c.races) {
            like += r.likes_cats ? 1 : 0;
            CHECK(r.likes_cats == (r.id == "core:catfolk"));
        }
        CHECK(like == 1);
        for (auto s = static_cast<std::size_t>(fauna::Species::Dog); s < fauna::kSpecies; ++s) {
            CHECK(fauna::habit(static_cast<fauna::Species>(s)) == fauna::Habit::Ground);
            CHECK_FALSE(fauna::model_file(static_cast<fauna::Species>(s)).empty());
        }
        CHECK(static_cast<std::size_t>(fauna::Species::Kitten) - static_cast<std::size_t>(fauna::Species::Cat) + 1 ==
              static_cast<std::size_t>(village::kCatLooks));
    }

    TEST_CASE("a wolf that comes into the dog's reach sets off the notice and the flight, and never gets to anybody") {
        // Without a dog first: the same wolf bites somebody.
        Game bare(core(), map_for(92), setup());
        const Scene none = scene(bare, false);
        beast(bare, CreatureKind::Wolf, none.spot, 0, -10);
        Seen without;
        for (int t = 0; t < 600; ++t) {
            bare.step();
            look(bare, without);
        }
        REQUIRE(without.attacks > 0);
        CHECK(without.barks == 0);
        // With the kennel.
        Game g(core(), map_for(92), setup());
        const Scene s = scene(g, true);
        const EntityId wolf = beast(g, CreatureKind::Wolf, s.spot, 0, -10);
        const std::int32_t whole = g.creatures().get(wolf)->health;
        Seen with;
        int fled = 0;
        bool held = false;
        for (int t = 0; t < 600; ++t) {
            g.step();
            look(g, with);
            fled = std::max(fled, fleeing_near(g, s.spot, 12));
            if (const Creature* w = g.creatures().get(wolf)) {
                held = held || w->bay > 0;
            }
            if (t == village::kDogTicks) {
                // By its first look.
                CHECK(with.barks == 1);
                CHECK(with.barked_at == static_cast<std::uint16_t>(CreatureKind::Wolf));
            }
        }
        CHECK(with.barks == 1);  // Once, however long the wolf stays.
        CHECK(with.attacks == 0);
        CHECK(fled > 0);
        CHECK(held);
        CHECK(g.player(0).deaths == 0);
        // And the dog bites: the wolf is hurt, or dead.
        const Creature* w = g.creatures().get(wolf);
        CHECK((w == nullptr || w->health < whole));
        // When the wolf is gone and a while has gone by, another one is news again.
        for (int t = 0; t < 3000 && g.creatures().get(wolf) != nullptr; ++t) {
            g.step();
        }
        REQUIRE(g.creatures().get(wolf) == nullptr);
        run(g, village::kBarkQuietTicks + 20);
        look(g, with);
        beast(g, CreatureKind::Wolf, s.spot, 0, -10);
        run(g, 2 * village::kDogTicks);
        look(g, with);
        CHECK(with.barks == 2);
    }

    TEST_CASE("the dog holds one wolf, the nearest, and not two") {
        Game g(core(), map_for(92), setup());
        const Scene s = scene(g, true);
        const EntityId near = beast(g, CreatureKind::Wolf, s.spot, 0, -6);
        const EntityId far = beast(g, CreatureKind::Wolf, s.spot, 3, -11);
        const std::int32_t whole = g.creatures().get(far)->health;
        run(g, village::kDogTicks + 1);
        REQUIRE(g.creatures().get(near) != nullptr);
        REQUIRE(g.creatures().get(far) != nullptr);
        CHECK(g.creatures().get(near)->bay > 0);
        CHECK(g.creatures().get(far)->bay == 0);
        CHECK(g.creatures().get(near)->health < whole);
        CHECK(g.creatures().get(far)->health == whole);
        // The one held stays where it is.
        const FixedVec2 where = g.creatures().get(near)->position;
        run(g, 40);
        if (const Creature* w = g.creatures().get(near); w != nullptr && w->bay > 0) {
            CHECK(w->position == where);
        }
    }

    TEST_CASE("a bear sets off the notice and the flight, and the dog leaves it alone") {
        Game g(core(), map_for(92), setup());
        const Scene s = scene(g, true);
        const EntityId bear = beast(g, CreatureKind::Bear, s.spot, 0, -10);
        const std::int32_t whole = g.creatures().get(bear)->health;
        Seen seen;
        int fled = 0;
        for (int t = 0; t < 3 * village::kDogTicks; ++t) {
            g.step();
            look(g, seen);
            fled = std::max(fled, fleeing_near(g, s.spot, 12));
            REQUIRE(g.creatures().get(bear) != nullptr);
            CHECK(g.creatures().get(bear)->bay == 0);
        }
        CHECK(seen.barks == 1);
        CHECK(seen.barked_at == static_cast<std::uint16_t>(CreatureKind::Bear));
        CHECK(fled > 0);
        CHECK(g.creatures().get(bear)->health == whole);
        // A deer is nobody to bark at.
        Game calm(core(), map_for(92), setup());
        const Scene c = scene(calm, true);
        beast(calm, CreatureKind::Deer, c.spot, 0, -8);
        Seen quiet;
        for (int t = 0; t < 100; ++t) {
            calm.step();
            look(calm, quiet);
        }
        CHECK(quiet.barks == 0);
    }

    TEST_CASE("a town with food to spare gets a cat a month, a house at a time; a hungry one loses them") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        std::vector<EntityId> houses;
        for (const auto& [dx, dz] : {std::pair{22, -14}, std::pair{22, 0}, std::pair{22, 14}}) {
            houses.push_back(put(g, "core:house", tx + dx, tz + dz));
            REQUIRE(houses.back().valid());
        }
        CHECK(cats(g) == 0);
        const std::uint32_t month = g.calendar_month_ticks();
        // A month for everybody to move in; then one cat with each month that begins.
        int had = 0;
        for (int m = 0; m < 6; ++m) {
            run(g, month);
            const int now = cats(g);
            MESSAGE("month " << m + 1 << ": food " << food(g) << ", people " << g.population(0) << ", cats " << now);
            CHECK(now >= had);
            CHECK(now <= had + 1);
            had = now;
        }
        CHECK(had == 3);  // Every house that has somebody; never two in one.
        for (const EntityId id : houses) {
            CHECK(at(g, id).cat >= 1);
            CHECK(at(g, id).cat <= village::kCatLooks);
        }
        // Nobody gathers anything: the food runs out, and the cats go, one a month.
        std::uint32_t t = 0;
        while (food(g) >= g.population(0) && t < 60 * month) {
            run(g, 100);
            t += 100;
        }
        REQUIRE(food(g) < g.population(0));
        for (int m = 0; m < 5 && cats(g) > 0; ++m) {
            const int before = cats(g);
            run(g, month);
            CHECK(cats(g) >= before - 1);
        }
        CHECK(cats(g) == 0);
    }

    TEST_CASE("a cat adds two to its house's environment, and two to the happiness of the cat people who live near it") {
        const auto play = [&](const char* people) {
            GameSetup rules = setup();
            rules.rules.races.fill(race(people));
            Game g(core(), map_for(92), rules);
            grant(g, "core:bread", 2000);
            const auto [tx, tz] = town(g);
            const EntityId first = put(g, "core:house", tx + 22, tz - 6);
            REQUIRE(first.valid());
            run(g, 2 * g.calendar_month_ticks());
            REQUIRE(at(g, first).cat != 0);
            // A second house 10 m from the first, and a third far away: nobody gets a cat in these.
            const EntityId second = put(g, "core:house", at(g, first).x, at(g, first).z + at(g, first).depth + 10);
            const EntityId third = put(g, "core:house", tx - 60, tz + 40);
            REQUIRE(second.valid());
            REQUIRE(third.valid());
            days(g, 3);
            struct Result {
                std::int32_t own, near, far, beauty;
            };
            Building copy = at(g, first);
            copy.cat = 0;
            Result r{extra(at(g, first)), at(g, second).cat == 0 && !at(g, second).residents.empty() ? extra(at(g, second)) : -99,
                     at(g, third).cat == 0 && !at(g, third).residents.empty() ? extra(at(g, third)) : -99,
                     at(g, first).desirability - g.desirability_at(middle(at(g, first)), &copy)};
            return r;
        };
        const auto cat_people = play("core:catfolk");
        CHECK(cat_people.beauty == village::kCatBeauty);
        CHECK(cat_people.own == village::kCatJoy);
        if (cat_people.near != -99) {
            CHECK(cat_people.near == village::kCatJoy);  // 10 m away.
        }
        if (cat_people.far != -99) {
            CHECK(cat_people.far == 0);
        }
        const auto humans = play("core:human");
        CHECK(humans.beauty == village::kCatBeauty);
        CHECK(humans.own == 0);
        MESSAGE("cat people: own " << cat_people.own << ", near " << cat_people.near << ", far " << cat_people.far << "; humans: own "
                                   << humans.own << ", near " << humans.near);
    }

    TEST_CASE("saving and loading keeps a wolf at bay, the dog's silence and the cats") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:house", tx + 22, tz).valid());
        run(g, 2 * g.calendar_month_ticks());
        REQUIRE(cats(g) == 1);
        const Scene s = scene(g, true);
        const EntityId wolf = beast(g, CreatureKind::Wolf, s.spot, 0, -8);
        run(g, village::kDogTicks + 3);
        REQUIRE(g.creatures().get(wolf) != nullptr);
        REQUIRE(g.creatures().get(wolf)->bay > 0);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.creatures().get(wolf)->bay == g.creatures().get(wolf)->bay);
        CHECK(at(loaded, s.kennel).rearm == at(g, s.kennel).rearm);
        CHECK(cats(loaded) == 1);
        run(g, 800);
        run(loaded, 800);
        CHECK(loaded.hash() == g.hash());
    }

    // Not a test: a saved game with a kennel, a coop and three houses with
    // food to spare (cats come with the months). Run it by name:
    //   salvaciudad_tests -ts=pets -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_pets.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a dog and cats" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        rules.rules.wildlife = Threat::None;
        Game g(core(), map_for(92), rules);
        grant(g, "core:bread", 3000);
        const auto [tx, tz] = town(g);
        for (int i = 0; i < 3; ++i) {
            REQUIRE(put(g, "core:house", tx + 18 + 10 * i, tz - 14).valid());
        }
        REQUIRE(put(g, "core:decor_kennel", tx + 18, tz + 10).valid());
        REQUIRE(put(g, "core:decor_kennel", tx + 30, tz + 10).valid());
        REQUIRE(put(g, "core:decor_chicken_coop", tx + 24, tz + 16).valid());
        run(g, 4 * g.calendar_month_ticks() + 50);
        save::SaveData data;
        data.header.name = "pets";
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
        REQUIRE(save::write_file(folder / "manual_pets.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << "); cats " << cats(g));
    }
}
