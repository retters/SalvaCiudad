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
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    return s;
}

// The test map with only the zones given, each `dx`, `dz` meters from the town's start.
struct Place {
    ZoneType type;
    std::int32_t dx, dz, radius;
};
MapData with_zones(std::initializer_list<Place> zones) {
    MapData m = map_for(92);
    REQUIRE(!m.starts.empty());
    m.zones.clear();
    for (const Place& p : zones) {
        m.zones.push_back({p.type, m.starts[0].x + Fixed::from_int(p.dx), m.starts[0].z + Fixed::from_int(p.dz), Fixed::from_int(p.radius)});
    }
    return m;
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

// A field of 8 x 8 of `owner` sown with `crop` every year, where it fits near it.
Field field_of(Game& g, EntityId owner, const char* crop) {
    const Building b = at(g, owner);
    for (std::int32_t r = 0; r <= 40; r += 2) {
        for (std::int32_t dz = -r; dz <= r; dz += 2) {
            for (std::int32_t dx = -r; dx <= r; dx += 2) {
                if (std::max(std::abs(dx), std::abs(dz)) != r) {
                    continue;
                }
                const std::int32_t x = b.x + dx, z = b.z + b.depth + 3 + dz;
                if (g.can_place_field(0, owner, x, z, 8, 8) != PlaceError::None) {
                    continue;
                }
                Command c;
                c.type = CommandType::PlaceField;
                c.entity = owner;
                c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                c.value = 8 | (8 << 8);
                g.apply(c);
                const DefIndex what = g.content().find_crop(crop);
                REQUIRE(what != kNoDef);
                for (int year = 0; year < static_cast<int>(kPlanYears); ++year) {
                    Command plan;
                    plan.type = CommandType::SetCrop;
                    plan.entity = owner;
                    plan.def = what;
                    plan.value = static_cast<std::int32_t>(at(g, owner).fields.size() - 1) | (year << 8);
                    g.apply(plan);
                }
                return at(g, owner).fields.back();
            }
        }
    }
    FAIL("no room for a field");
    return {};
}

void trace(Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1) {
    Command c;
    c.type = CommandType::Trace;
    c.def = g.content().find_building(def);
    REQUIRE(c.def != kNoDef);
    c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
    c.value = x1;
    c.value2 = z1;
    g.apply(c);
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

struct Seen {
    int rabbits = 0;
    int hens = 0;
    int young = 0;
};
void look(Game& g, Seen& s) {
    for (const Game::Event& e : g.take_events()) {
        s.rabbits += e.kind == Game::Event::Kind::Rabbits ? 1 : 0;
        s.hens += e.kind == Game::Event::Kind::Lynx && e.other == 0 ? 1 : 0;
        s.young += e.kind == Game::Event::Kind::Lynx && e.other == 1 ? 1 : 0;
    }
}

}  // namespace

TEST_SUITE("smallgame") {
    TEST_CASE("the maps have zones of rabbits on open ground and of the lynx in the woods, after the zones of before") {
        const Content& c = test::core_content();
        CHECK(c.crops[c.find_crop("core:vegetables")].rabbits);
        CHECK_FALSE(c.crops[c.find_crop("core:wheat")].rabbits);
        for (const std::uint64_t seed : {91ull, 92ull}) {
            const MapData& m = map_for(seed);
            CHECK(m.generator_version == worldgen::kGeneratorVersion);
            int rabbits = 0, lynx = 0;
            bool new_ones = false;
            for (const Zone& z : m.zones) {
                const bool is_new = z.type == ZoneType::Rabbits || z.type == ZoneType::Lynx;
                new_ones = new_ones || is_new;
                CHECK(is_new == new_ones);  // They come last.
                const Terrain t = m.terrain_at(z.x.floor_int(), z.z.floor_int());
                if (z.type == ZoneType::Rabbits) {
                    ++rabbits;
                    CHECK((t == Terrain::Meadow || t == Terrain::Grass));
                } else if (z.type == ZoneType::Lynx) {
                    ++lynx;
                    CHECK(t == Terrain::ForestFloor);
                }
            }
            MESSAGE("seed " << seed << ": " << rabbits << " zones of rabbits, " << lynx << " of lynx, of " << m.zones.size());
            CHECK(rabbits >= 1);
        }
        for (const fauna::Species s : {fauna::Species::Rabbit, fauna::Species::Lynx, fauna::Species::Wildcat}) {
            CHECK(fauna::habit(s) == fauna::Habit::Ground);
            CHECK_FALSE(fauna::model_file(s).empty());
        }
    }

    TEST_CASE("neither rabbits nor the lynx walk the map; by a lynx there are half the rabbits") {
        Game g(core(), with_zones({{ZoneType::Rabbits, 90, 0, 50}, {ZoneType::Rabbits, -150, 120, 50}, {ZoneType::Lynx, 200, 0, 60}}),
               setup());
        CHECK(g.creatures().size() == 0);
        REQUIRE(g.zone_animals().size() == 3);
        // 90 to 200 m: within the lynx's 60 m of both edges. The other is far.
        CHECK(g.zone_room(0) == village::kRabbits / 2);
        CHECK(g.zone_room(1) == village::kRabbits);
        CHECK(g.zone_room(2) == 1);
        CHECK(g.zone_animals()[0] == village::kRabbits / 2);
        CHECK(g.zone_animals()[1] == village::kRabbits);
        run(g, 6 * g.calendar_month_ticks());
        CHECK(g.zone_animals()[0] == village::kRabbits / 2);
        CHECK(g.zone_animals()[1] == village::kRabbits);
        CHECK(g.creatures().size() == 0);
        const auto [tx, tz] = town(g);
        // The lynx lives within 60 m of the middle of its zone, and is near what is within 60 m more.
        const std::int32_t sx = g.map().starts[0].x.floor_int(), sz = g.map().starts[0].z.floor_int();
        CHECK(g.lynx_near(sx + 200 - 119, sz));
        CHECK_FALSE(g.lynx_near(sx + 200 - 122, sz));
        CHECK(g.lynx_near(sx + 200 - 160, sz, 50));
        CHECK_FALSE(g.lynx_near(sx - 150, sz + 120, 50));
        (void)tx;
        (void)tz;
    }

    TEST_CASE("the hunter brings a little meat and no hide from the rabbits, when there is no bigger game") {
        Game g(core(), with_zones({{ZoneType::Rabbits, 70, 0, 40}}), setup());
        grant(g, "core:bread", 2000);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:storehouse", tx - 26, tz).valid());
        const EntityId lodge = put(g, "core:hunter", tx + 24, tz);
        REQUIRE(lodge.valid());
        const std::int32_t meat = have(g, "core:meat");
        const std::int32_t hides = have(g, "core:hide");
        run(g, 3000);
        const std::int32_t hunted = village::kRabbits - g.zone_animals()[0];
        MESSAGE("rabbits hunted: " << hunted << "; meat " << have(g, "core:meat") - meat);
        CHECK(hunted > 0);
        CHECK(have(g, "core:hide") == hides);
        CHECK(have(g, "core:meat") <= meat + village::kRabbitMeat * (hunted + 1));
        CHECK(have(g, "core:meat") > meat);
        // With deer in reach they go for the deer, and leave the rabbits alone.
        Game big(core(), with_zones({{ZoneType::Rabbits, 60, 0, 40}, {ZoneType::Deer, 90, 40, 60}}), setup());
        grant(big, "core:bread", 2000);
        REQUIRE(put(big, "core:hunter", tx + 24, tz).valid());
        const std::int32_t meat_before = have(big, "core:meat");
        bool deer_taken = false;
        for (std::uint32_t t = 0; t < 6000 && !deer_taken; ++t) {
            big.step();
            deer_taken = big.zone_animals()[1] < 16 || have(big, "core:hide") > 0;
        }
        CHECK(deer_taken);
        CHECK(big.zone_animals()[0] == village::kRabbits);
        CHECK(have(big, "core:meat") != meat_before);
    }

    TEST_CASE("rabbits eat of the vegetables of a field among many of them, unless a fence, a dog or a lynx keeps them off") {
        const DefIndex vegetables = test::core_content().find_crop("core:vegetables");
        const DefIndex wheat = test::core_content().find_crop("core:wheat");
        Game g(core(), with_zones({{ZoneType::Rabbits, 40, 30, 70}}), setup());
        const auto [tx, tz] = town(g);
        const std::int32_t x = tx + 30, z = tz + 24;
        CHECK(g.rabbits_eat(0, vegetables, x, z, 8, 8));
        CHECK_FALSE(g.rabbits_eat(0, wheat, x, z, 8, 8));                // They do not eat wheat.
        CHECK_FALSE(g.rabbits_eat(0, vegetables, x - 200, z, 8, 8));     // Out of their zone.
        // A fence along half its border: eight modules for 32 m. Seven are not enough.
        trace(g, "core:picket_fence", x, z - 2, x + 6, z - 2);
        trace(g, "core:picket_fence", x - 2, z, x - 2, z + 4);
        CHECK(g.rabbits_eat(0, vegetables, x, z, 8, 8));
        trace(g, "core:picket_fence", x - 2, z + 6, x - 2, z + 6);
        CHECK_FALSE(g.rabbits_eat(0, vegetables, x, z, 8, 8));
        // A dog: a kennel within 12 m of the field.
        const std::int32_t x2 = tx + 60, z2 = tz + 50;
        REQUIRE(g.rabbits_eat(0, vegetables, x2, z2, 8, 8));
        const EntityId far = place_at(g, g.content().find_building("core:decor_kennel"), x2 + 24, z2);
        REQUIRE(far.valid());
        CHECK(g.rabbits_eat(0, vegetables, x2, z2, 8, 8));
        REQUIRE(place_at(g, g.content().find_building("core:decor_kennel"), x2 + 14, z2 + 2).valid());
        CHECK_FALSE(g.rabbits_eat(0, vegetables, x2, z2, 8, 8));
        // A lynx near: half the rabbits, and it hunts those that come.
        Game hunted(core(), with_zones({{ZoneType::Rabbits, 40, 30, 70}, {ZoneType::Lynx, 150, 30, 50}}), setup());
        CHECK_FALSE(hunted.rabbits_eat(0, vegetables, x, z, 8, 8));
        // (A hunter does not thin them out enough: two come back every month. Only the lynx does.)
        CHECK(hunted.zone_animals()[0] < village::kManyRabbits);
    }

    TEST_CASE("a field of vegetables among rabbits brings in a fifth less, and the town is told") {
        const auto harvest = [](bool rabbits, int& told) {
            Game g(core(), rabbits ? with_zones({{ZoneType::Rabbits, 30, 30, 90}}) : with_zones({}), setup());
            grant(g, "core:bread", 3000);
            const auto [tx, tz] = town(g);
            const EntityId farm = put(g, "core:farm", tx + 24, tz + 10);
            REQUIRE(farm.valid());
            const Field f = field_of(g, farm, "core:vegetables");
            CHECK(g.rabbits_eat(0, g.content().find_crop("core:vegetables"), f.x, f.z, f.w, f.d) == rabbits);
            Seen seen;
            std::int32_t pending = 0;
            for (std::uint32_t t = 0; t < g.year_ticks() && pending == 0; ++t) {
                g.step();
                look(g, seen);
                const Field& now = at(g, farm).fields[0];
                if (now.state == FieldState::Ripe) {
                    pending = now.pending;
                }
            }
            told = seen.rabbits;
            return pending;
        };
        int told_with = 0, told_without = 0;
        const std::int32_t without = harvest(false, told_without);
        const std::int32_t with = harvest(true, told_with);
        MESSAGE("harvest: " << without << " with no rabbits, " << with << " among them");
        REQUIRE(without > 0);
        CHECK(with == std::max(1, without * (100 - village::kRabbitLoss) / 100));
        CHECK(told_with == 1);
        CHECK(told_without == 0);
    }

    TEST_CASE("a lynx takes hens from a coop with no fence and no dog, and a young one a year from a fold with no dog") {
        Game g(core(), with_zones({{ZoneType::Lynx, 60, 0, 50}}), setup());
        grant(g, "core:bread", 4000);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:storehouse", tx - 26, tz).valid());
        const EntityId coop = put(g, "core:decor_chicken_coop", tx + 24, tz - 24);
        const EntityId kept = put(g, "core:decor_chicken_coop", tx - 30, tz - 40);
        REQUIRE(coop.valid());
        REQUIRE(kept.valid());
        REQUIRE(put(g, "core:decor_kennel", at(g, kept).x + 5, at(g, kept).z).valid());
        REQUIRE(g.lynx_near(at(g, coop).x, at(g, coop).z));
        const EntityId fold = put(g, "core:sheepfold", tx + 24, tz + 14);
        REQUIRE(fold.valid());
        REQUIRE_FALSE(g.guarded(at(g, fold).x, at(g, fold).z, 10, 10));
        // Its pasture, marked before the shepherd comes.
        bool marked = false;
        for (std::int32_t dx = 12; dx < 40 && !marked; dx += 2) {
            if (g.can_place_field(0, fold, at(g, fold).x + dx, at(g, fold).z, 16, 20) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceField;
                c.entity = fold;
                c.position = {Fixed::from_int(at(g, fold).x + dx), Fixed::from_int(at(g, fold).z)};
                c.value = 16 | (20 << 8);
                g.apply(c);
                marked = true;
            }
        }
        REQUIRE(marked);
        (void)g.take_events();
        Seen seen;
        for (std::uint32_t t = 0; t < g.year_ticks() - 3 * g.calendar_day_ticks(); t += 50) {
            run(g, 50);
            look(g, seen);
        }
        MESSAGE("in a year by a lynx: " << seen.hens << " hens and " << seen.young << " young taken; hens left "
                                        << int(at(g, coop).flock) << ", flock " << at(g, fold).females + at(g, fold).males);
        CHECK(seen.hens > 0);
        CHECK(at(g, kept).flock == 4);
        CHECK(seen.young == 1);
        CHECK(at(g, fold).females + at(g, fold).males == 5);  // Six, but for the one it took.
        // The same fold with a dog by it: six.
        Game safe(core(), with_zones({{ZoneType::Lynx, 60, 0, 50}}), setup());
        grant(safe, "core:bread", 4000);
        const EntityId guarded = put(safe, "core:sheepfold", tx + 24, tz + 14);
        REQUIRE(guarded.valid());
        REQUIRE(put(safe, "core:decor_kennel", at(safe, guarded).x - 4, at(safe, guarded).z + 2).valid());
        REQUIRE(safe.guarded(at(safe, guarded).x, at(safe, guarded).z, 10, 10));
        for (std::int32_t dx = 12; dx < 40; dx += 2) {
            if (at(safe, guarded).fields.empty() &&
                safe.can_place_field(0, guarded, at(safe, guarded).x + dx, at(safe, guarded).z, 16, 20) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceField;
                c.entity = guarded;
                c.position = {Fixed::from_int(at(safe, guarded).x + dx), Fixed::from_int(at(safe, guarded).z)};
                c.value = 16 | (20 << 8);
                safe.apply(c);
            }
        }
        REQUIRE(!at(safe, guarded).fields.empty());
        Seen none;
        for (std::uint32_t t = 0; t < 30 * safe.calendar_day_ticks(); t += 50) {
            run(safe, 50);
            look(safe, none);
        }
        CHECK(none.young == 0);
        CHECK(at(safe, guarded).females + at(safe, guarded).males == 6);
    }

    TEST_CASE("saving and loading keeps the rabbits there are") {
        Game g(core(), with_zones({{ZoneType::Rabbits, 70, 0, 40}, {ZoneType::Lynx, 250, 200, 50}}), setup());
        grant(g, "core:bread", 2000);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:hunter", tx + 24, tz).valid());
        run(g, 1500);
        REQUIRE(g.zone_animals()[0] < village::kRabbits);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), with_zones({{ZoneType::Rabbits, 70, 0, 40}, {ZoneType::Lynx, 250, 200, 50}}), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.zone_animals() == g.zone_animals());
        run(g, 1500);
        run(loaded, 1500);
        CHECK(loaded.hash() == g.hash());
    }

    // Not a test: a saved game with a zone of rabbits around the town, a lynx
    // in reach of half of it and a farm with a field of vegetables. Run it
    // by name:
    //   salvaciudad_tests -ts=smallgame -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_smallgame.scsave: copy it to the
    // saves folder and load it.
    TEST_CASE("manual: a saved game with rabbits and a lynx" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), with_zones({{ZoneType::Rabbits, 20, 10, 60}, {ZoneType::Lynx, -60, -40, 40}}), rules);
        grant(g, "core:bread", 3000);
        const auto [tx, tz] = town(g);
        const EntityId farm = put(g, "core:farm", tx + 24, tz + 10);
        REQUIRE(farm.valid());
        (void)field_of(g, farm, "core:vegetables");
        REQUIRE(put(g, "core:decor_chicken_coop", tx - 20, tz - 16).valid());
        run(g, 300);
        save::SaveData data;
        data.header.name = "smallgame";
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
        REQUIRE(save::write_file(folder / "manual_smallgame.scsave", data));
        MESSAGE("rabbits " << g.zone_animals()[0] << "; lynx near the coop: " << g.lynx_near(tx - 20, tz - 16));
    }
}
