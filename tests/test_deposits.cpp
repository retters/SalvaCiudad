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

// The base game with small deposits, so that they are worked out soon.
std::shared_ptr<const Content> small_deposits(std::int32_t amount) {
    auto c = std::make_shared<Content>(test::core_content());
    for (FeatureDef& f : c->features) {
        if (f.kind == FeatureType::ClayDeposit || f.kind == FeatureType::CoalDeposit || f.kind == FeatureType::GoldDeposit) {
            f.amount = amount;
        }
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

void provide(Game& g) {
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// The town center goes up to the level a mine needs.
void level_up(Game& g, std::int32_t tier) {
    for (int i = 0; i < 6 && g.tier(0) < tier; ++i) {
        Command c;
        c.type = CommandType::DevLevel;
        g.apply(c);
    }
    REQUIRE(g.tier(0) >= tier);
}

// A building of `def` near (x, z), where it fits; built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = building(g, def);
    for (std::int32_t r = 0; r <= 16; ++r) {
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
                Command done;
                done.type = CommandType::DevBuild;
                g.apply(done);
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

// A deposit set down by the developer tools; its index.
std::uint32_t plant(Game& g, FeatureType type, std::int32_t x, std::int32_t z, std::uint8_t size = 0) {
    Command c;
    c.type = CommandType::DevFeature;
    c.def = static_cast<std::uint16_t>(type);
    c.count = size;
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

std::pair<std::int32_t, std::int32_t> town(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    return {tc->x, tc->z};
}

// How many times a workplace told that it has nothing left to work.
int exhausted_events(Game& g, EntityId who) {
    int n = 0;
    for (const Game::Event& e : g.take_events()) {
        n += e.kind == Game::Event::Kind::Exhausted && e.entity == who ? 1 : 0;
    }
    return n;
}

// A mine of `def` by the town and, some meters from it, a deposit of `type`
// (or none). Runs until the deposit is gone or the time is.
struct Worked {
    EntityId mine;
    std::uint32_t deposit = 0;
    int told = 0;
};
Worked work_out(Game& g, const char* def, std::optional<FeatureType> type, int ticks = 20000) {
    provide(g);
    const auto [tx, tz] = town(g);
    Worked w;
    w.mine = put(g, def, tx + 18, tz);
    REQUIRE(w.mine.valid());
    const Building at = *g.buildings().get(w.mine);
    if (type) {
        w.deposit = plant(g, *type, at.x + 14, at.z + 2);
    }
    (void)g.take_events();
    for (int t = 0; t < ticks; t += 20) {
        run(g, 20);
        w.told += exhausted_events(g, w.mine);
        if (type && g.nodes()[w.deposit].amount <= 0 && t > 400) {
            // A little longer: what is in hand gets home, and the mine finds out.
            for (int k = 0; k < 60; ++k) {
                run(g, 20);
                w.told += exhausted_events(g, w.mine);
            }
            break;
        }
    }
    return w;
}

}  // namespace

TEST_SUITE("deposits") {
    TEST_CASE("the base game's deposits of clay, coal and gold, and who works them") {
        const Content& c = test::core_content();
        const struct {
            FeatureType type;
            const char* gives;
            const char* mine;
            std::int32_t tier;
        } kinds[] = {{FeatureType::ClayDeposit, "core:clay", "core:clay_pit", 0},
                     {FeatureType::CoalDeposit, "core:coal", "core:coal_mine", 2},
                     {FeatureType::GoldDeposit, "core:gold", "core:gold_mine", 3}};
        for (const auto& k : kinds) {
            CHECK(is_deposit(k.type));
            const FeatureDef* fd = c.feature(k.type);
            REQUIRE(fd != nullptr);
            CAPTURE(fd->id);
            CHECK(fd->resource == c.find_resource(k.gives));
            CHECK(fd->regrow_days == 0);
            CHECK(fd->seasons == 0);
            CHECK(fd->models.size() == 1);
            const BuildingDef& mine = c.buildings[c.find_building(k.mine)];
            CHECK(mine.work == WorkKind::Gather);
            CHECK(mine.gathers == (1u << static_cast<unsigned>(k.type)));
            CHECK(mine.tier == k.tier);
            CHECK(mine.workers == 2);
            CHECK(mine.recipes.empty());
        }
        CHECK(is_deposit(FeatureType::StoneDeposit));
        CHECK_FALSE(is_deposit(FeatureType::Stone));
        CHECK_FALSE(is_deposit(FeatureType::IronOre));
        // Gold comes out slowly, and the mine keeps none: it goes to the town's gold.
        CHECK(c.feature(FeatureType::GoldDeposit)->work > 2 * c.feature(FeatureType::CoalDeposit)->work);
        CHECK(c.buildings[c.find_building("core:gold_mine")].storage == 0);
        // The kiln still makes coal of logs, half again as slowly as before (80).
        const BuildingDef& kiln = c.buildings[c.find_building("core:charcoal_kiln")];
        REQUIRE(kiln.recipes.size() == 1);
        CHECK(c.recipes[kiln.recipes[0]].work == 120);
        CHECK(c.find_recipe("core:dig_clay") == kNoDef);
    }

    TEST_CASE("a clay pit with no bank in its reach digs nothing, and says so") {
        Game g(core(), map_for(92), setup());
        // (Away from the map's own banks: none within the pit's reach.)
        const auto [tx, tz] = town(g);
        for (const MapFeature& f : g.map().features) {
            if (f.type == FeatureType::ClayDeposit) {
                const std::int64_t dx = f.x.floor_int() - (tx + 18), dz = f.z.floor_int() - tz;
                REQUIRE(dx * dx + dz * dz > 100 * 100);
            }
        }
        const std::int32_t clay = have(g, "core:clay");
        const Worked w = work_out(g, "core:clay_pit", std::nullopt, 3000);
        CHECK(have(g, "core:clay") == clay);
        CHECK(g.buildings().get(w.mine)->supply == Supply::Exhausted);
        CHECK(w.told == 1);
    }

    TEST_CASE("with a bank, the pit digs it all, the bank is gone and the pit says so once") {
        Game g(small_deposits(14), map_for(92), setup());
        const std::int32_t clay = have(g, "core:clay");
        const Worked w = work_out(g, "core:clay_pit", FeatureType::ClayDeposit);
        CHECK(g.nodes()[w.deposit].amount == 0);
        CHECK(have(g, "core:clay") == clay + 14);
        CHECK(g.buildings().get(w.mine)->supply == Supply::Exhausted);
        CHECK(w.told == 1);
        // Its ground is free again.
        const MapFeature& f = g.map().features[w.deposit];
        CHECK(g.nav().walkable(f.x.floor_int() / 2, f.z.floor_int() / 2));
    }

    TEST_CASE("the coal mine brings home what the seam had") {
        Game g(small_deposits(20), map_for(92), setup());
        level_up(g, 2);
        const std::int32_t coal = have(g, "core:coal");
        const Worked w = work_out(g, "core:coal_mine", FeatureType::CoalDeposit);
        CHECK(g.nodes()[w.deposit].amount == 0);
        CHECK(have(g, "core:coal") == coal + 20);
        CHECK(w.told == 1);
    }

    TEST_CASE("the gold mine adds to the town's gold") {
        Game g(small_deposits(12), map_for(92), setup());
        level_up(g, 3);
        const std::int32_t gold = g.gold(0);
        const Worked w = work_out(g, "core:gold_mine", FeatureType::GoldDeposit);
        CHECK(g.nodes()[w.deposit].amount == 0);
        CHECK(g.gold(0) == gold + 12);
        // None stays at the mine: it is in the town center, as the rest of the town's gold.
        CHECK(g.buildings().get(w.mine)->stock.empty());
    }

    TEST_CASE("a deposit stands on its ground: nothing is built on it, nobody walks over it, several work it at once") {
        Game g(core(), map_for(92), setup());
        provide(g);
        level_up(g, 2);
        const auto [tx, tz] = town(g);
        const EntityId mine = put(g, "core:coal_mine", tx + 18, tz);
        REQUIRE(mine.valid());
        const Building at = *g.buildings().get(mine);
        const std::int32_t x = at.x + 16, z = at.z + 2;
        REQUIRE(g.can_place(0, building(g, "core:palisade"), x, z, 0) == PlaceError::None);
        const std::uint32_t seam = plant(g, FeatureType::CoalDeposit, x, z, 1);
        CHECK(g.can_place(0, building(g, "core:palisade"), x, z, 0) == PlaceError::Blocked);
        CHECK(g.can_place(0, building(g, "core:palisade"), x - 2, z - 2, 0) == PlaceError::Blocked);
        CHECK_FALSE(g.nav().walkable(x / 2, z / 2));
        // Its two miners at it together.
        bool together = false;
        for (int t = 0; t < 4000 && !together; ++t) {
            g.step();
            int at_it = 0;
            for (const Villager& v : g.villagers().data()) {
                at_it += v.job == mine && v.node == seam + 1 && v.task == Task::Gather ? 1 : 0;
            }
            together = at_it >= 2;
        }
        CHECK(together);
    }

    TEST_CASE("every start has clay and coal within a walk, and the map of before is where it was") {
        for (const auto& [seed, size, players, sea] :
             {std::tuple{91ull, MapSize::Small, 1, Sea::None}, std::tuple{92ull, MapSize::Small, 1, Sea::None},
              std::tuple{2026ull, MapSize::Medium, 4, Sea::None}, std::tuple{7ull, MapSize::Small, 2, Sea::OneSide}}) {
            MapSettings s;
            s.seed = seed;
            s.size = size;
            s.players = static_cast<std::uint8_t>(players);
            s.sea = sea;
            const std::optional<MapData> m = generate_map(s, test::core_content());
            REQUIRE(m.has_value());
            CAPTURE(seed);
            CHECK(m->generator_version == worldgen::kGeneratorVersion);
            std::map<FeatureType, int> count;
            for (const MapFeature& f : m->features) {
                ++count[f.type];
            }
            CHECK(count[FeatureType::ClayDeposit] > 0);
            CHECK(count[FeatureType::CoalDeposit] > 0);
            GameSetup gs = setup();
            gs.players = static_cast<std::uint8_t>(players);
            const Game g(core(), *m, gs);
            for (const StartPosition& start : m->starts) {
                // The nearest of a kind that the town can walk to; its distance squared.
                const auto nearest = [&](FeatureType t) {
                    std::int64_t best = -1;
                    for (const MapFeature& f : m->features) {
                        const std::int64_t dx = (f.x - start.x).floor_int(), dz = (f.z - start.z).floor_int();
                        if (f.type != t || (best >= 0 && dx * dx + dz * dz >= best)) {
                            continue;
                        }
                        const std::int32_t half = deposit_half_side(f.size) + 2;
                        bool walk = false;
                        for (const auto& [ox, oz] : {std::pair{half, 0}, std::pair{-half, 0}, std::pair{0, half}, std::pair{0, -half}}) {
                            walk = walk || g.nav().connected({start.x, start.z + Fixed::from_int(12)},
                                                             {f.x + Fixed::from_int(ox), f.z + Fixed::from_int(oz)});
                        }
                        if (walk) {
                            best = dx * dx + dz * dz;
                        }
                    }
                    return best;
                };
                const std::int64_t clay = nearest(FeatureType::ClayDeposit), coal = nearest(FeatureType::CoalDeposit);
                REQUIRE(clay >= 0);
                REQUIRE(coal >= 0);
                CHECK(clay <= static_cast<std::int64_t>(worldgen::kStartClayRadius) * worldgen::kStartClayRadius);
                CHECK(coal <= static_cast<std::int64_t>(worldgen::kStartCoalRadius) * worldgen::kStartCoalRadius);
                // And none where the town center goes.
                CHECK(clay > 30 * 30);
                CHECK(coal > 30 * 30);
            }
            // No deposit shares its ground with anything: nothing had to make room for it.
            for (const MapFeature& d : m->features) {
                if (d.type != FeatureType::ClayDeposit && d.type != FeatureType::CoalDeposit && d.type != FeatureType::GoldDeposit) {
                    continue;
                }
                const std::int32_t half = deposit_half_side(d.size);
                for (const MapFeature& f : m->features) {
                    if (&f != &d) {
                        const bool on_it = std::abs(f.x.floor_int() - d.x.floor_int()) <= half &&
                                           std::abs(f.z.floor_int() - d.z.floor_int()) <= half;
                        CHECK_FALSE(on_it);
                    }
                }
            }
        }
    }

    TEST_CASE("saving and loading keeps a seam half worked") {
        Game g(small_deposits(40), map_for(92), setup());
        provide(g);
        level_up(g, 2);
        const auto [tx, tz] = town(g);
        const EntityId mine = put(g, "core:coal_mine", tx + 18, tz);
        REQUIRE(mine.valid());
        const Building at = *g.buildings().get(mine);
        // A large one: as it wears down it becomes a medium one, then a small one.
        const std::uint32_t seam = plant(g, FeatureType::CoalDeposit, at.x + 16, at.z + 2, 2);
        const std::int32_t whole = g.nodes()[seam].amount;
        CHECK(whole == deposit_amount(40, 2));
        for (int t = 0; t < 20000 && g.map().features[seam].size == 2; ++t) {
            g.step();
        }
        REQUIRE(g.map().features[seam].size < 2);
        REQUIRE(g.nodes()[seam].amount > 0);
        BinaryWriter w;
        g.save(w);
        Game loaded(small_deposits(40), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, small_deposits(40)));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.nodes()[seam].amount == g.nodes()[seam].amount);
        CHECK(loaded.map().features[seam].size == g.map().features[seam].size);
        const MapFeature& f = g.map().features[seam];
        CHECK_FALSE(loaded.nav().walkable(f.x.floor_int() / 2, f.z.floor_int() / 2));
        run(g, 800);
        run(loaded, 800);
        CHECK(loaded.hash() == g.hash());
    }

    // Not a test: a saved game with a bank of clay, a seam of coal and a vein
    // of gold, each with its pit or mine beside it, and the three sizes of
    // each in a row. Run it by name:
    //   salvasprosperia_tests -ts=deposits -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_deposits.scsave: copy it to the
    // saves folder and load it.
    TEST_CASE("manual: a saved game with deposits of clay, coal and gold being worked" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        level_up(g, 3);
        const auto [tx, tz] = town(g);
        const struct {
            const char* mine;
            FeatureType type;
            std::int32_t dz;
        } rows[] = {{"core:clay_pit", FeatureType::ClayDeposit, -22},
                    {"core:coal_mine", FeatureType::CoalDeposit, 0},
                    {"core:gold_mine", FeatureType::GoldDeposit, 22}};
        for (const auto& row : rows) {
            const EntityId mine = put(g, row.mine, tx + 20, tz + row.dz);
            REQUIRE(mine.valid());
            const Building at = *g.buildings().get(mine);
            for (std::uint8_t size = 0; size < kDepositSizes; ++size) {
                plant(g, row.type, at.x + 16 + 14 * size, at.z + 3, size);
            }
        }
        run(g, 1500);
        save::SaveData data;
        data.header.name = "deposits";
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
        REQUIRE(save::write_file(folder / "manual_deposits.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << ")");
    }
}
