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

// The base game with folds that come with no male.
std::shared_ptr<const Content> no_male() {
    auto c = std::make_shared<Content>(test::core_content());
    for (HerdDef& h : c->herds) {
        h.start_male = false;
    }
    return c;
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

// The four seasons, with a year of the usual length.
GameSetup setup() {
    GameSetup s;
    s.seed = 15;
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

// A field of `w` by `d` for `owner` (a fold's pasture, a farm's field), where it fits near it. False: nowhere.
bool mark(Game& g, EntityId owner, std::int32_t w, std::int32_t d) {
    const Building b = at(g, owner);
    for (std::int32_t r = 0; r <= 40; r += 2) {
        for (std::int32_t dz = -r; dz <= r; dz += 2) {
            for (std::int32_t dx = -r; dx <= r; dx += 2) {
                if (std::max(std::abs(dx), std::abs(dz)) != r) {
                    continue;
                }
                const std::int32_t x = b.x + dx, z = b.z + b.depth + 2 + dz;
                if (g.can_place_field(0, owner, x, z, w, d) != PlaceError::None) {
                    continue;
                }
                Command c;
                c.type = CommandType::PlaceField;
                c.entity = owner;
                c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                c.value = w | (d << 8);
                g.apply(c);
                return true;
            }
        }
    }
    return false;
}

void unmark(Game& g, EntityId owner) {
    Command c;
    c.type = CommandType::RemoveField;
    c.entity = owner;
    c.value = 0;
    g.apply(c);
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

// A town with food for years and room in its stores, a fold and its shepherd.
EntityId fold_with_shepherd(Game& g) {
    grant(g, "core:bread", 4000);
    const auto [tx, tz] = town(g);
    REQUIRE(put(g, "core:storehouse", tx - 26, tz).valid());
    const EntityId fold = put(g, "core:sheepfold", tx + 24, tz - 20);
    REQUIRE(fold.valid());
    for (int t = 0; t < 600 && at(g, fold).workers.empty(); ++t) {
        g.step();
    }
    REQUIRE(!at(g, fold).workers.empty());
    return fold;
}

// Until the first day of the next `season`, and a day more (the folds' round).
void until(Game& g, Season season) {
    while (g.calendar().season == season) {
        g.step();
    }
    while (g.calendar().season != season) {
        g.step();
    }
    run(g, 2 * g.calendar_day_ticks());
}

int flock(const Building& b) {
    return b.females + b.males;
}

}  // namespace

TEST_SUITE("herds") {
    TEST_CASE("the base game's sheep, their fold and what is made of their wool") {
        const Content& c = test::core_content();
        const DefIndex sheep = c.find_herd("core:sheep");
        REQUIRE(sheep != kNoDef);
        const HerdDef& h = c.herds[sheep];
        CHECK(h.start == 3);
        CHECK(h.start_male);
        CHECK(h.area == 40);
        CHECK(h.most == 16);
        CHECK(h.male_price == 30);
        REQUIRE(h.spring.size() == 1);
        CHECK(h.spring[0].resource == c.find_resource("core:wool"));
        CHECK(h.spring[0].amount == 2);
        CHECK(h.cull.size() == 2);
        const BuildingDef& fold = c.buildings[c.find_building("core:sheepfold")];
        REQUIRE(fold.herds.size() == 1);
        CHECK(fold.herds[0] == sheep);
        CHECK(fold.workers == 1);
        CHECK(fold.work == WorkKind::None);
        CHECK(fold.work_radius > 0);
        CHECK(c.find_building(fold.pasture_fence) != kNoDef);
        // The weaver makes the same cloth of wool as of flax.
        const BuildingDef& weaver = c.buildings[c.find_building("core:weaver")];
        const DefIndex of_wool = c.find_recipe("core:weave_wool");
        const DefIndex of_flax = c.find_recipe("core:weave_linen");
        REQUIRE(of_wool != kNoDef);
        CHECK(std::count(weaver.recipes.begin(), weaver.recipes.end(), of_wool) == 1);
        REQUIRE(c.recipes[of_wool].outputs.size() == 1);
        REQUIRE(c.recipes[of_flax].outputs.size() == 1);
        CHECK(c.recipes[of_wool].outputs[0].resource == c.recipes[of_flax].outputs[0].resource);
        CHECK(c.recipes[of_wool].outputs[0].amount == c.recipes[of_flax].outputs[0].amount);
        CHECK(c.recipes[of_wool].work == c.recipes[of_flax].work);
        for (const fauna::Species s : {fauna::Species::Sheep, fauna::Species::Ram}) {
            CHECK(fauna::habit(s) == fauna::Habit::Ground);
            CHECK_FALSE(fauna::model_file(s).empty());
        }
    }

    TEST_CASE("a flock with its ram goes from four to six in its first spring, and stops at the room of its pasture") {
        Game g(core(), map_for(92), setup());
        REQUIRE(g.calendar().season == Season::Spring);
        const EntityId fold = fold_with_shepherd(g);
        CHECK(at(g, fold).females == 3);
        CHECK(at(g, fold).males == 1);
        // 16 x 20 m: room for eight.
        REQUIRE(mark(g, fold, 16, 20));
        CHECK(g.herd_room(at(g, fold)) == 8);
        run(g, 2 * g.calendar_day_ticks());
        CHECK(flock(at(g, fold)) == 6);
        CHECK(at(g, fold).males == 1);
        // Once a spring.
        run(g, 10 * g.calendar_day_ticks());
        CHECK(flock(at(g, fold)) == 6);
        until(g, Season::Spring);
        CHECK(flock(at(g, fold)) == 8);  // Three more would be nine: two fit.
        until(g, Season::Spring);
        CHECK(flock(at(g, fold)) == 8);
        // A larger pasture, and it grows again; never over sixteen.
        unmark(g, fold);
        REQUIRE(mark(g, fold, 32, 24));
        CHECK(g.herd_room(at(g, fold)) == 16);
        until(g, Season::Spring);
        CHECK(flock(at(g, fold)) == 12);  // Seven females: four young.
        until(g, Season::Spring);
        CHECK(flock(at(g, fold)) == 16);
        until(g, Season::Spring);
        CHECK(flock(at(g, fold)) == 16);
    }

    TEST_CASE("with no pasture, or with no shepherd, a flock does not grow") {
        Game g(core(), map_for(92), setup());
        const EntityId fold = fold_with_shepherd(g);
        run(g, 3 * g.calendar_day_ticks());
        CHECK(flock(at(g, fold)) == 4);
        CHECK(have(g, "core:wool") == 6);  // Sheared all the same.
        until(g, Season::Autumn);
        CHECK(flock(at(g, fold)) == 4);  // And it keeps what it came with.
        // Nobody to look after it: nothing.
        Game alone(core(), map_for(92), setup());
        const auto [tx, tz] = town(alone);
        const EntityId other = put(alone, "core:sheepfold", tx + 24, tz - 20);
        REQUIRE(other.valid());
        Command c;
        c.type = CommandType::SetWorkers;
        c.entity = other;
        c.value = 0;
        alone.apply(c);
        REQUIRE(mark(alone, other, 16, 20));
        run(alone, 20 * alone.calendar_day_ticks());
        REQUIRE(at(alone, other).workers.empty());
        CHECK(flock(at(alone, other)) == 4);
        CHECK(have(alone, "core:wool") == 0);
    }

    TEST_CASE("without a ram there are no young; another one costs thirty of gold") {
        Game g(no_male(), map_for(92), setup());
        const EntityId fold = fold_with_shepherd(g);
        REQUIRE(mark(g, fold, 16, 20));
        CHECK(at(g, fold).males == 0);
        run(g, 3 * g.calendar_day_ticks());
        CHECK(at(g, fold).females == 3);
        CHECK(have(g, "core:wool") == 6);
        const std::int32_t gold = g.gold(0);
        REQUIRE(gold >= 30);
        Command buy;
        buy.type = CommandType::BuyMale;
        buy.entity = fold;
        g.apply(buy);
        CHECK(g.rejected_commands() == 0);
        CHECK(at(g, fold).males == 1);
        CHECK(g.gold(0) == gold - 30);
        // It has one: not another.
        g.apply(buy);
        CHECK(g.rejected_commands() == 1);
        CHECK(g.gold(0) == gold - 30);
        until(g, Season::Spring);
        CHECK(at(g, fold).females == 5);
        // Not of a house, and not without the gold.
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx - 30, tz + 30);
        REQUIRE(house.valid());
        buy.entity = house;
        g.apply(buy);
        CHECK(g.rejected_commands() == 2);
        Game poor(no_male(), map_for(92), setup());
        const EntityId second = fold_with_shepherd(poor);
        const EntityId third = put(poor, "core:sheepfold", at(poor, second).x, at(poor, second).z + 30);
        const EntityId fourth = put(poor, "core:sheepfold", at(poor, second).x + 30, at(poor, second).z + 30);
        const EntityId fifth = put(poor, "core:sheepfold", at(poor, second).x + 30, at(poor, second).z);
        int bought = 0;
        for (const EntityId id : {second, third, fourth, fifth}) {
            REQUIRE(id.valid());
            buy.entity = id;
            poor.apply(buy);
            bought += at(poor, id).males;
        }
        CHECK(bought == gold / 30);  // As many as the gold pays for.
        CHECK(poor.gold(0) == gold - 30 * bought);
        CHECK(poor.rejected_commands() == 4u - static_cast<unsigned>(bought));
    }

    TEST_CASE("the wool is carried to the storage, and the weaver makes cloth of it") {
        // (A weaver that needs no town level.)
        auto c = std::make_shared<Content>(test::core_content());
        c->buildings[c->find_building("core:weaver")].tier = 0;
        Game g(c, map_for(92), setup());
        const EntityId fold = fold_with_shepherd(g);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:weaver", tx - 26, tz + 20).valid());
        REQUIRE(have(g, "core:flax") == 0);
        const std::int32_t linen = have(g, "core:linen");
        run(g, 3 * g.calendar_day_ticks());
        REQUIRE(have(g, "core:wool") == 6);
        // Until the three bolts are woven.
        for (std::uint32_t t = 0; t < 6000 && have(g, "core:linen") < linen + 3; ++t) {
            g.step();
        }
        CHECK(have(g, "core:linen") == linen + 3);
        CHECK(have(g, "core:wool") == 0);
        CHECK(at(g, fold).stock.empty());
    }

    TEST_CASE("in autumn the animals over the pasture's room become meat and hides") {
        Game g(core(), map_for(92), setup());
        const EntityId fold = fold_with_shepherd(g);
        REQUIRE(mark(g, fold, 16, 20));
        run(g, 2 * g.calendar_day_ticks());
        REQUIRE(flock(at(g, fold)) == 6);
        // A smaller pasture before the autumn: room for two, but a fold keeps the four it came with.
        unmark(g, fold);
        REQUIRE(mark(g, fold, 8, 10));
        REQUIRE(g.herd_room(at(g, fold)) == 2);
        const std::int32_t hides = have(g, "core:hide");
        until(g, Season::Autumn);
        CHECK(flock(at(g, fold)) == 4);
        CHECK(at(g, fold).males == 1);  // The ram is never one of them.
        CHECK(have(g, "core:hide") == hides + 2);
        // Once: the rest of the autumn changes nothing.
        run(g, 10 * g.calendar_day_ticks());
        CHECK(flock(at(g, fold)) == 4);
        CHECK(have(g, "core:hide") == hides + 2);
    }

    TEST_CASE("a pasture is one, within reach, not over water and not over another field") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        // A fold by the water, if the town has any within a walk.
        std::optional<std::pair<std::int32_t, std::int32_t>> water;
        for (std::int32_t r = 20; r < 160 && !water; r += 4) {
            for (std::int32_t dz = -r; dz <= r && !water; dz += 4) {
                for (std::int32_t dx = -r; dx <= r && !water; dx += 4) {
                    if (std::max(std::abs(dx), std::abs(dz)) == r && g.map().water_at(tx + dx, tz + dz)) {
                        water = std::pair{tx + dx, tz + dz};
                    }
                }
            }
        }
        REQUIRE(water.has_value());
        const EntityId fold = put(g, "core:sheepfold", water->first, water->second);
        REQUIRE(fold.valid());
        const Building b = at(g, fold);
        // Over the water nearest to it.
        std::optional<std::pair<std::int32_t, std::int32_t>> wet;
        for (std::int32_t dz = -40; dz <= 40 && !wet; ++dz) {
            for (std::int32_t dx = -40; dx <= 40 && !wet; ++dx) {
                if (g.map().water_at(b.x + dx, b.z + dz) && dx * dx + dz * dz < 36 * 36) {
                    wet = std::pair{b.x + dx - 2, b.z + dz - 2};
                }
            }
        }
        REQUIRE(wet.has_value());
        const PlaceError over_water = g.can_place_field(0, fold, wet->first, wet->second, 6, 6);
        CHECK(over_water != PlaceError::None);
        CHECK((over_water == PlaceError::Water || over_water == PlaceError::Blocked || over_water == PlaceError::TooSteep));
        // Too large, and too far.
        CHECK(g.can_place_field(0, fold, b.x, b.z + 14, kMaxPastureSide + 1, 8) == PlaceError::BadSize);
        CHECK(g.can_place_field(0, fold, b.x + 200, b.z, 8, 8) == PlaceError::TooFar);
        // Over a farm's field.
        const EntityId farm = put(g, "core:farm", b.x - 24, b.z - 24);
        REQUIRE(farm.valid());
        REQUIRE(mark(g, farm, 8, 8));
        const Field field = at(g, farm).fields[0];
        const std::int64_t fx = field.x + 4 - (b.x + 5), fz = field.z + 4 - (b.z + 5);
        if (fx * fx + fz * fz <= 50 * 50) {
            CHECK(g.can_place_field(0, fold, field.x + 2, field.z + 2, 8, 8) == PlaceError::Blocked);
        }
        // One pasture.
        REQUIRE(mark(g, fold, 8, 8));
        CHECK(at(g, fold).fields.size() == 1);
        CHECK_FALSE(mark(g, fold, 8, 8));
        // And nothing is sown in it.
        for (const DefIndex crop : at(g, fold).fields[0].plan) {
            CHECK(crop == kNoDef);
        }
        // Nor is anything built on it.
        const Field pasture = at(g, fold).fields[0];
        CHECK(g.can_place(0, g.content().find_building("core:house"), pasture.x + 1, pasture.z + 1, 0) != PlaceError::None);
    }

    TEST_CASE("saving and loading keeps a fold's flock, its pasture and the seasons it has had") {
        Game g(core(), map_for(92), setup());
        const EntityId fold = fold_with_shepherd(g);
        REQUIRE(mark(g, fold, 16, 20));
        until(g, Season::Summer);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(flock(at(loaded, fold)) == 6);
        CHECK(at(loaded, fold).herd_spring == at(g, fold).herd_spring);
        CHECK(loaded.herd_room(at(loaded, fold)) == 8);
        until(g, Season::Spring);
        until(loaded, Season::Spring);
        CHECK(loaded.hash() == g.hash());
        CHECK(flock(at(loaded, fold)) == 8);
    }

    // Not a test: a saved game with a fold, its pasture and its flock. Run
    // it by name:
    //   salvaciudad_tests -ts=herds -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_herds.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a sheepfold" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        const EntityId fold = fold_with_shepherd(g);
        REQUIRE(mark(g, fold, 20, 16));
        run(g, 400);
        save::SaveData data;
        data.header.name = "herds";
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
        REQUIRE(save::write_file(folder / "manual_herds.scsave", data));
        MESSAGE("flock " << flock(at(g, fold)) << ", pasture room " << g.herd_room(at(g, fold)));
    }
}
