#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
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

// The test map with no game but `zones` zones of mammoths, one upon the
// other, 70 m from the start over dry ground.
MapData mammoth_map(int zones = 1) {
    MapData m = map_for(92);
    m.zones.clear();
    REQUIRE(!m.starts.empty());
    const std::int32_t sx = m.starts[0].x.floor_int(), sz = m.starts[0].z.floor_int();
    for (int a = 0; a < 16; ++a) {
        const double angle = a * 3.14159265358979 / 8.0;
        bool dry = true;
        for (int d = 0; d <= 90 && dry; d += 2) {
            const auto x = static_cast<std::int32_t>(sx + std::cos(angle) * d), z = static_cast<std::int32_t>(sz + std::sin(angle) * d);
            dry = x > 8 && z > 8 && x < m.size - 8 && z < m.size - 8 && !m.water_at(x, z);
        }
        if (!dry) {
            continue;
        }
        const Fixed x = Fixed::from_int(static_cast<std::int32_t>(sx + std::cos(angle) * 70));
        const Fixed z = Fixed::from_int(static_cast<std::int32_t>(sz + std::sin(angle) * 70));
        for (int k = 0; k < zones; ++k) {
            m.zones.push_back({ZoneType::Mammoths, x, z, Fixed::from_int(40)});
        }
        return m;
    }
    FAIL("no dry way out of the start");
    return m;
}

GameSetup setup(std::uint8_t seasons = 0b1111) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = seasons;
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    return s;
}
constexpr std::uint8_t kWinterOnly = 0b1000;

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

std::int32_t in(const Building& b, const Game& g, const char* resource) {
    const DefIndex r = g.content().find_resource(resource);
    std::int32_t n = 0;
    for (const Stock& s : b.stock) {
        n += s.resource == r ? s.amount : 0;
    }
    return n;
}

// A town that lacks nothing through a winter, with a storehouse and a
// hunters' lodge between its center and the mammoths.
EntityId lodge_town(Game& g, std::int32_t weapons) {
    grant(g, "core:bread", 6000);
    grant(g, "core:firewood", 3000);
    grant(g, "core:clothes", 100);
    if (weapons > 0) {
        grant(g, "core:weapons", weapons);
    }
    const Building tc = at(g, g.player(0).town_center);  // (A copy: building moves the others.)
    REQUIRE(put(g, "core:storehouse", tc.x - 26, tc.z).valid());
    // Homes with a hearth for everybody: it is winter.
    for (int n = 0; n < 5; ++n) {
        REQUIRE(put(g, "core:house", tc.x - 20 + n * 10, tc.z - 22).valid());
    }
    const Zone& zone = g.map().zones[0];
    const std::int32_t lx = (tc.x + zone.x.floor_int()) / 2, lz = (tc.z + zone.z.floor_int()) / 2;
    const EntityId lodge = put(g, "core:hunter", lx, lz);
    REQUIRE(lodge.valid());
    return lodge;
}

std::int32_t mammoths(const Game& g) {
    std::int32_t n = 0;
    for (std::size_t z = 0; z < g.map().zones.size(); ++z) {
        n += g.map().zones[z].type == ZoneType::Mammoths ? g.zone_animals()[z] : 0;
    }
    return n;
}

std::uint64_t only_without(const Content& c, std::initializer_list<std::string_view> ids) {
    std::uint64_t mask = 0;
    for (std::size_t b = 0; b < c.flora.biomes.size(); ++b) {
        if (std::find(ids.begin(), ids.end(), c.flora.biomes[b].id) == ids.end()) {
            mask |= std::uint64_t{1} << b;
        }
    }
    return mask;
}

}  // namespace

TEST_SUITE("mammoths") {
    TEST_CASE("the base game: the lodge takes weapons, ivory is only to sell, and the cold biomes have mammoths") {
        const Content& c = test::core_content();
        const DefIndex lodge = c.find_building("core:hunter");
        REQUIRE(lodge != kNoDef);
        CHECK(c.buildings[lodge].hunt_arms == c.find_resource("core:weapons"));
        CHECK(c.buildings[lodge].workers == 2);
        const DefIndex ivory = c.find_resource("core:ivory");
        REQUIRE(ivory != kNoDef);
        CHECK(c.resources[ivory].sell_only);
        CHECK(c.resources[ivory].value > 3 * c.resources[c.find_resource("core:weapons")].value);
        CHECK(c.resources[ivory].category == ResourceCategory::Good);
        // Nothing is made of it.
        for (const RecipeDef& r : c.recipes) {
            for (const ResourceAmount& input : r.inputs) {
                CHECK(input.resource != ivory);
            }
        }
        int cold = 0;
        for (const BiomeDef& b : c.flora.biomes) {
            cold += b.mammoths ? 1 : 0;
            CHECK(b.mammoths == (b.id == "core:mountain" || b.id == "core:boreal"));
        }
        CHECK(cold == 2);
    }

    TEST_CASE("there are no mammoths in summer and there are in winter, with a notice the day they come") {
        Game g(core(), mammoth_map(), setup());
        (void)lodge_town(g, 0);
        REQUIRE(g.calendar().season == Season::Spring);
        CHECK(mammoths(g) == 0);
        CHECK(g.zone_room(0) == 0);
        (void)g.take_events();
        int notices = 0;
        bool winter = false, spring_again = false;
        std::uint64_t came_day = 0;
        for (std::uint32_t t = 0; t < g.year_ticks() + 3 * g.calendar_day_ticks(); ++t) {
            g.step();
            const Season season = g.calendar().season;
            for (const Game::Event& e : g.take_events()) {
                if (e.kind == Game::Event::Kind::Mammoths) {
                    ++notices;
                    came_day = g.calendar_day();
                    CHECK(e.owner == 0);
                    CHECK(e.value == village::kMammoths);
                    CHECK(e.at.x == g.map().zones[0].x);
                    CHECK(e.at.z == g.map().zones[0].z);
                    CHECK(season == Season::Winter);
                }
            }
            if (season == Season::Winter) {
                winter = true;
                // (From the day's round on: the first ticks of the day belong to the night before.)
                if (g.calendar_day() > came_day && notices > 0) {
                    CHECK(mammoths(g) == village::kMammoths);
                    CHECK(g.zone_room(0) == village::kMammoths);
                }
            } else {
                if (winter && season == Season::Spring && g.tick() % g.calendar_day_ticks() > 2) {
                    spring_again = true;
                }
                if (!winter || spring_again) {
                    CHECK(mammoths(g) == 0);
                }
            }
        }
        CHECK(winter);
        CHECK(spring_again);
        CHECK(notices == 1);
    }

    TEST_CASE("a town far from every herd hears nothing, and a game without winter has no mammoths") {
        MapData far = mammoth_map();
        // The zone goes to the far corner of the map.
        const bool east = far.starts[0].x.floor_int() < far.size / 2, south = far.starts[0].z.floor_int() < far.size / 2;
        far.zones[0].x = Fixed::from_int(east ? far.size - 30 : 30);
        far.zones[0].z = Fixed::from_int(south ? far.size - 30 : 30);
        Game g(core(), far, setup());
        grant(g, "core:bread", 6000);
        grant(g, "core:firewood", 3000);
        int notices = 0;
        bool there = false;
        for (std::uint32_t t = 0; t < g.year_ticks(); ++t) {
            g.step();
            there = there || mammoths(g) > 0;
            for (const Game::Event& e : g.take_events()) {
                notices += e.kind == Game::Event::Kind::Mammoths ? 1 : 0;
            }
        }
        CHECK(there);
        CHECK(notices == 0);

        Game mild(core(), mammoth_map(), setup(0b0111));
        grant(mild, "core:bread", 6000);
        for (std::uint32_t t = 0; t < mild.year_ticks(); ++t) {
            mild.step();
            REQUIRE(mammoths(mild) == 0);
        }
    }

    TEST_CASE("without weapons, or with one hunter alone, nobody goes for the mammoths") {
        // Two hunters and not a weapon in the town.
        Game unarmed(core(), mammoth_map(), setup(kWinterOnly));
        const EntityId lodge = lodge_town(unarmed, 0);
        REQUIRE(mammoths(unarmed) == village::kMammoths);
        run(unarmed, 4000);
        REQUIRE(at(unarmed, lodge).workers.size() == 2);
        CHECK(mammoths(unarmed) == village::kMammoths);
        CHECK(have(unarmed, "core:ivory") == 0);
        CHECK(unarmed.big_game(at(unarmed, lodge)).zones == 1);
        CHECK(unarmed.big_game(at(unarmed, lodge)).animals == village::kMammoths);

        // Weapons in the storehouse and one hunter: the laborers do not even take them to the lodge.
        Game alone(core(), mammoth_map(), setup(kWinterOnly));
        const EntityId single = lodge_town(alone, 6);
        Command c;
        c.type = CommandType::SetWorkers;
        c.entity = single;
        c.value = 1;
        alone.apply(c);
        run(alone, 4000);
        REQUIRE(at(alone, single).workers.size() == 1);
        CHECK(mammoths(alone) == village::kMammoths);
        CHECK(have(alone, "core:ivory") == 0);
        CHECK(in(at(alone, single), alone, "core:weapons") == 0);
        CHECK(have(alone, "core:weapons") == 6);
    }

    TEST_CASE("a hunt of the two hunters gives meat, hides and ivory, and spends a weapon") {
        Game g(core(), mammoth_map(), setup(kWinterOnly));
        const EntityId lodge = lodge_town(g, 6);
        const std::int32_t hides = have(g, "core:hide");
        // The laborers bring the lodge its weapons: no more than it keeps.
        bool armed = false;
        std::int32_t meat = 0, weapons = 0;
        std::uint32_t t = 0;
        for (; t < 6000 && mammoths(g) == village::kMammoths; ++t) {
            meat = have(g, "core:meat");
            weapons = have(g, "core:weapons");
            g.step();
            const std::int32_t kept = in(at(g, lodge), g, "core:weapons");
            CHECK(kept <= village::kLodgeArms);
            armed = armed || kept > 0;
        }
        REQUIRE(mammoths(g) == village::kMammoths - 1);
        CHECK(armed);
        MESSAGE("the first mammoth fell at tick " << t);
        // That tick: the meat (a load in the hands of each, the rest at the lodge), the hides and the ivory.
        CHECK(have(g, "core:meat") - meat == village::kMammothMeat);
        CHECK(have(g, "core:weapons") == weapons - 1);
        CHECK(have(g, "core:ivory") == village::kMammothIvory);
        CHECK(in(at(g, lodge), g, "core:ivory") == village::kMammothIvory);
        CHECK(have(g, "core:hide") - hides == village::kMammothHides);
        int carrying = 0;
        for (const EntityId id : at(g, lodge).workers) {
            const Villager* v = g.villagers().get(id);
            REQUIRE(v != nullptr);
            carrying += v->carrying.resource == g.content().find_resource("core:meat") && v->carrying.amount > 0 ? 1 : 0;
        }
        CHECK(carrying == 2);
        // Another one follows: a weapon each, and the lodge is given more when it has none.
        for (std::uint32_t k = 0; k < 8000 && mammoths(g) > village::kMammoths - 2; ++k) {
            g.step();
            CHECK(in(at(g, lodge), g, "core:weapons") <= village::kLodgeArms);
        }
        REQUIRE(mammoths(g) == village::kMammoths - 2);
        CHECK(have(g, "core:weapons") == 6 - 2);
        CHECK(have(g, "core:ivory") == 2 * village::kMammothIvory);
        // The ivory goes to the storehouse like any good, when there is a load of it.
        run(g, 1500);
        CHECK(in(at(g, lodge), g, "core:ivory") < have(g, "core:ivory"));
    }

    TEST_CASE("over many hunts some hunters come back wounded and nobody dies of the wound alone") {
        Game g(core(), mammoth_map(10), setup(kWinterOnly));
        const EntityId lodge = lodge_town(g, 40);
        const std::int32_t herd = mammoths(g);
        REQUIRE(herd == 10 * village::kMammoths);
        (void)g.take_events();
        // (In a year that is all winter the herds are whole again every year: there is always one to hunt.)
        int hunts = 0, wounded = 0;
        std::int32_t lowest = village::kHealthMax, before = herd;
        std::vector<EntityId> hunters;
        for (std::uint32_t t = 0; t < 4 * g.year_ticks(); ++t) {
            if (t % g.calendar_month_ticks() == 0) {
                // The town lacks nothing, however long the winter.
                grant(g, "core:bread", std::max(0, 6000 - have(g, "core:bread")));
                grant(g, "core:firewood", std::max(0, 3000 - have(g, "core:firewood")));
            }
            g.step();
            const std::int32_t now = mammoths(g);
            hunts += now < before ? before - now : 0;
            before = now;
            for (const Game::Event& e : g.take_events()) {
                if (e.kind == Game::Event::Kind::Wounded) {
                    ++wounded;
                    const Villager* v = g.villagers().get(e.entity);
                    REQUIRE(v != nullptr);
                    CHECK(v->job == lodge);
                    CHECK(v->health >= village::kWoundLeast);
                    CHECK(v->health <= village::kHealthMax - village::kMammothWound + 2);  // (It began to heal this tick.)
                }
            }
            for (const EntityId id : at(g, lodge).workers) {
                if (const Villager* v = g.villagers().get(id)) {
                    lowest = std::min(lowest, v->health);
                    if (std::find(hunters.begin(), hunters.end(), id) == hunters.end()) {
                        hunters.push_back(id);
                    }
                }
            }
        }
        // A weapon each, and none lost on the way to the lodge.
        CHECK(have(g, "core:weapons") == 40 - hunts);
        MESSAGE(hunts << " hunts: " << wounded << " wounded; the lowest health of a hunter: " << lowest << "; " << hunters.size()
                      << " hunters in all");
        REQUIRE(hunts >= 16);
        // About one in four.
        CHECK(wounded >= hunts / 8);
        CHECK(wounded <= hunts / 2);
        CHECK(lowest >= village::kWoundLeast);
        // Everyone who hunted is alive.
        for (const EntityId id : hunters) {
            CHECK(g.villagers().get(id) != nullptr);
        }
    }

    TEST_CASE("the generator puts zones of mammoths in the cold biomes only") {
        const Content& c = test::core_content();
        int with = 0;
        for (const std::uint64_t seed : {3ull, 21ull, 92ull, 140ull}) {
            MapSettings s;
            s.seed = seed;
            s.size = MapSize::Medium;
            s.players = 2;
            const std::optional<MapData> m = generate_map(s, c);
            REQUIRE(m.has_value());
            std::vector<const Zone*> zones;
            bool after = false;
            for (const Zone& z : m->zones) {
                if (z.type > ZoneType::Mammoths) {
                    continue;  // (What came after them: the glades of phase 112.)
                }
                if (z.type != ZoneType::Mammoths) {
                    CHECK_FALSE(after);  // They are the last ones: the zones of before keep their places.
                    continue;
                }
                after = true;
                const std::int32_t x = z.x.floor_int(), zz = z.z.floor_int();
                REQUIRE(m->biome_at(x, zz) < c.flora.biomes.size());
                CHECK(c.flora.biomes[m->biome_at(x, zz)].mammoths);
                CHECK_FALSE(m->water_at(x, zz));
                for (const StartPosition& start : m->starts) {
                    const std::int64_t dx = start.x.floor_int() - x, dz = start.z.floor_int() - zz;
                    CHECK(dx * dx + dz * dz >= static_cast<std::int64_t>(worldgen::kMammothFromStart) * worldgen::kMammothFromStart);
                }
                for (const Zone* o : zones) {
                    const std::int64_t dx = o->x.floor_int() - x, dz = o->z.floor_int() - zz;
                    CHECK(dx * dx + dz * dz >= static_cast<std::int64_t>(worldgen::kMammothSpacing) * worldgen::kMammothSpacing);
                }
                zones.push_back(&z);
            }
            MESSAGE("seed " << seed << ": " << zones.size() << " zones of mammoths");
            with += zones.empty() ? 0 : 1;

            // The same map without the cold biomes: none.
            s.biomes = only_without(c, {"core:mountain", "core:boreal"});
            const std::optional<MapData> warm = generate_map(s, c);
            REQUIRE(warm.has_value());
            for (const Zone& z : warm->zones) {
                CHECK(z.type != ZoneType::Mammoths);
            }
        }
        CHECK(with >= 2);
    }

    TEST_CASE("saving and loading keeps a hunt under way") {
        Game g(core(), mammoth_map(), setup(kWinterOnly));
        const EntityId lodge = lodge_town(g, 6);
        // Until one of the two is at the herd, waiting or at work.
        bool there = false;
        for (std::uint32_t t = 0; t < 6000 && !there; ++t) {
            g.step();
            for (const EntityId id : at(g, lodge).workers) {
                const Villager* v = g.villagers().get(id);
                there = there || (v != nullptr && v->task == Task::Hunt && v->timer != 0);
            }
        }
        REQUIRE(there);
        REQUIRE(mammoths(g) == village::kMammoths);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), mammoth_map(), setup(kWinterOnly));
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        run(g, 3000);
        run(loaded, 3000);
        CHECK(loaded.hash() == g.hash());
        CHECK(mammoths(loaded) == mammoths(g));
        CHECK(mammoths(g) < village::kMammoths);
        CHECK(have(loaded, "core:ivory") == have(g, "core:ivory"));
    }

    // Not a test: a saved game in winter with a lodge by a herd of mammoths.
    //   salvaciudad_tests -ts=mammoths -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_mammoths.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a lodge by a herd of mammoths" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup(kWinterOnly);
        rules.rules.fog = FogMode::None;
        Game g(core(), mammoth_map(), rules);
        const EntityId lodge = lodge_town(g, 6);
        run(g, 300);
        save::SaveData data;
        data.header.name = "mammoths";
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
        REQUIRE(save::write_file(folder / "manual_mammoths.scsave", data));
        MESSAGE("lodge at (" << at(g, lodge).x << ", " << at(g, lodge).z << "), the herd at (" << g.map().zones[0].x.floor_int() << ", "
                             << g.map().zones[0].z.floor_int() << ")");
    }
}
