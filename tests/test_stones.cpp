#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <tuple>
#include <utility>
#include <vector>

#include "game/map_scene.h"
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

// The base game with a house that costs `stone` of stone and nothing else.
std::shared_ptr<const Content> stone_house(std::int32_t stone) {
    auto c = std::make_shared<Content>(test::core_content());
    BuildingDef& house = c->buildings[c->find_building("core:house")];
    house.cost = {{c->find_resource("core:stone"), stone}};
    house.build_work = 60;
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

std::pair<std::int32_t, std::int32_t> town(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    return {tc->x, tc->z};
}

// A building of `def` near (x, z), where it fits; left as a site, or built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z, bool built) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
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
                if (built) {
                    Command done;
                    done.type = CommandType::DevBuild;
                    g.apply(done);
                }
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

// Everything the loose stones of the map hold.
std::int32_t loose(const Game& g) {
    std::int32_t n = 0;
    for (std::size_t i = 0; i < g.nodes().size(); ++i) {
        n += g.map().features[i].type == FeatureType::LooseStones ? g.nodes()[i].amount : 0;
    }
    return n;
}

std::int32_t stone(const Game& g) {
    return g.stored(0)[g.content().find_resource("core:stone")];
}

bool complete(const Game& g, EntityId id) {
    const Building* b = g.buildings().get(id);
    return b != nullptr && b->state == BuildingState::Complete;
}

// Everything a map has but its loose stones: what generator 9 made.
std::uint64_t old_map_hash(const MapData& m, std::uint32_t& features) {
    BinaryWriter w;
    features = 0;
    for (const MapFeature& f : m.features) {
        if (f.type == FeatureType::LooseStones) {
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
    return fnv1a64(w.bytes());
}

}  // namespace

TEST_SUITE("stones") {
    TEST_CASE("the base game's rocks: loose stones, boulders and outcrops, each of its biome's stone") {
        const Content& c = test::core_content();
        const FeatureDef* stones = c.feature(FeatureType::LooseStones);
        REQUIRE(stones != nullptr);
        CHECK(stones->loose);
        CHECK(stones->amount == 6);
        CHECK(stones->resource == c.find_resource("core:stone"));
        CHECK(stones->regrow_days == 0);
        CHECK(stones->rock_of_biome);
        CHECK(stones->models.size() == static_cast<std::size_t>(RockKind::Count));
        const FeatureDef* boulder = c.feature(FeatureType::Stone);
        REQUIRE(boulder != nullptr);
        CHECK_FALSE(boulder->loose);
        CHECK(boulder->amount == 40);
        CHECK(boulder->rock_of_biome);
        CHECK(boulder->models.size() == static_cast<std::size_t>(RockKind::Count));
        const FeatureDef* outcrop = c.feature(FeatureType::StoneDeposit);
        REQUIRE(outcrop != nullptr);
        CHECK_FALSE(outcrop->loose);
        CHECK(outcrop->models.size() == kDepositSizes + 2);  // Its sizes, and the small one in mossy and in sandstone.
        CHECK_FALSE(is_deposit(FeatureType::LooseStones));
        const BuildingDef& cutter = c.buildings[c.find_building("core:stonecutter")];
        for (const FeatureType t : {FeatureType::Stone, FeatureType::StoneDeposit, FeatureType::LooseStones}) {
            CHECK(((cutter.gathers >> static_cast<unsigned>(t)) & 1u) != 0);
        }
        // The stone of the biomes: mossy where it is wet, sandstone where it is dry.
        const auto rock = [&](const char* id) {
            for (const BiomeDef& b : c.flora.biomes) {
                if (b.id == id) {
                    return static_cast<RockKind>(b.rock);
                }
            }
            FAIL("no biome " << id);
            return RockKind::Count;
        };
        CHECK(rock("core:temperate") == RockKind::Gray);
        CHECK(rock("core:mountain") == RockKind::Gray);
        CHECK(rock("core:boreal") == RockKind::Mossy);
        CHECK(rock("core:riverside") == RockKind::Mossy);
        CHECK(rock("core:savanna") == RockKind::Sandstone);
        CHECK(rock("core:mediterranean") == RockKind::Sandstone);
    }

    TEST_CASE("each rock is drawn with the stone of its biome, and a small deposit is the outcrop of its biome") {
        const Content& c = test::core_content();
        MapData m = map_for(92);
        // A place of each stone, if the map has it.
        std::map<std::uint8_t, std::pair<std::int32_t, std::int32_t>> at;
        for (std::int32_t z = 8; z < m.size - 8; z += 8) {
            for (std::int32_t x = 8; x < m.size - 8; x += 8) {
                const std::size_t biome = m.biome_at(x, z);
                if (biome < c.flora.biomes.size()) {
                    at.emplace(c.flora.biomes[biome].rock, std::pair{x, z});
                }
            }
        }
        REQUIRE(at.count(0) == 1);
        MESSAGE("stones on this map: " << at.size());
        for (const auto& [kind, where] : at) {
            MapFeature f;
            f.x = Fixed::from_int(where.first);
            f.z = Fixed::from_int(where.second);
            f.scale = Fixed::one();
            for (const FeatureType t : {FeatureType::LooseStones, FeatureType::Stone}) {
                f.type = t;
                CHECK(visual_slot(c, f, &m) == feature_slot(c, t, kind));
                CHECK(visual_slot(c, f) == feature_slot(c, t, 0));  // Without a map: gray.
            }
            f.type = FeatureType::StoneDeposit;
            f.size = 0;
            CHECK(visual_slot(c, f, &m) == feature_slot(c, f.type, kind == 0 ? 0 : kDepositSizes + kind - 1u));
            // The medium and the large are the same everywhere (they are looks of the small one's slot).
            f.size = 1;
            CHECK(visual_slot(c, f, &m) == feature_slot(c, f.type, 0));
            CHECK(feature_look(c, f, {}) == 1);
        }
    }

    TEST_CASE("a town with no stonecutter and no stone left finishes a site with loose stones") {
        // The house asks for all the stone the town has and six more.
        Game probe(core(), map_for(92), setup());
        const std::int32_t stored = stone(probe);
        REQUIRE(stored > 0);
        Game g(stone_house(stored + 6), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 14, tz, false);
        REQUIRE(house.valid());
        const Building at = *g.buildings().get(house);
        // Two heaps beside it, nearer than any of the map's.
        const std::uint32_t a = plant(g, FeatureType::LooseStones, at.x + 10, at.z + 2);
        const std::uint32_t b = plant(g, FeatureType::LooseStones, at.x + 12, at.z + 5);
        CHECK(g.nodes()[a].amount == 6);
        const std::int32_t before = loose(g);
        for (int t = 0; t < 6000 && !complete(g, house); ++t) {
            g.step();
        }
        CHECK(complete(g, house));
        // Just the six that were missing, from those heaps; nothing went to the storage.
        CHECK(loose(g) == before - 6);
        CHECK(g.nodes()[a].amount + g.nodes()[b].amount == 6);
        CHECK(stone(g) == 0);
        for (const Villager& v : g.villagers().data()) {
            CHECK(v.carrying.amount == 0);
        }
    }

    TEST_CASE("with stone in the storage, laborers leave the loose stones alone") {
        Game probe(core(), map_for(92), setup());
        const std::int32_t stored = stone(probe);
        REQUIRE(stored >= 6);
        Game g(stone_house(6), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 14, tz, false);
        REQUIRE(house.valid());
        const Building at = *g.buildings().get(house);
        plant(g, FeatureType::LooseStones, at.x + 10, at.z + 2);
        const std::int32_t before = loose(g);
        for (int t = 0; t < 6000 && !complete(g, house); ++t) {
            g.step();
        }
        CHECK(complete(g, house));
        run(g, 600);
        CHECK(loose(g) == before);
        CHECK(stone(g) == stored - 6);
    }

    TEST_CASE("loose stones too far from the site, or with nobody building, stay where they are") {
        Game probe(core(), map_for(92), setup());
        const std::int32_t stored = stone(probe);
        Game g(stone_house(stored + 6), map_for(92), setup());
        provide(g);
        run(g, 1500);  // Nothing to build: nobody picks anything up.
        const std::int32_t before = loose(g);
        CHECK(before > 0);
        const auto [tx, tz] = town(g);
        // The map's own heaps near the site are taken away first: none within reach.
        const EntityId house = put(g, "core:house", tx + 14, tz, false);
        REQUIRE(house.valid());
        const Building at = *g.buildings().get(house);
        std::int32_t in_reach = 0;
        for (std::size_t i = 0; i < g.nodes().size(); ++i) {
            const MapFeature& f = g.map().features[i];
            const std::int64_t dx = f.x.floor_int() - (at.x + at.width / 2), dz = f.z.floor_int() - (at.z + at.depth / 2);
            if (f.type == FeatureType::LooseStones && dx * dx + dz * dz <= village::kLooseMeters * village::kLooseMeters) {
                in_reach += g.nodes()[i].amount;
            }
        }
        MESSAGE("loose stones within reach of the site: " << in_reach << " of " << before);
        for (int t = 0; t < 8000 && !complete(g, house); ++t) {
            g.step();
        }
        // With enough of them within reach the house is finished; whatever happens, none from beyond is touched.
        CHECK(complete(g, house) == (in_reach >= 6));
        CHECK(loose(g) >= before - in_reach);
        CHECK(loose(g) == before - (complete(g, house) ? 6 : in_reach));
    }

    TEST_CASE("the stonecutter takes loose stones too, and boulders as ever") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId cutter = put(g, "core:stonecutter", tx + 16, tz, true);
        REQUIRE(cutter.valid());
        const Building at = *g.buildings().get(cutter);
        const std::uint32_t heap = plant(g, FeatureType::LooseStones, at.x + 10, at.z + 2);
        const std::uint32_t boulder = plant(g, FeatureType::Stone, at.x + 12, at.z - 4);
        const std::int32_t had = stone(g);
        bool at_heap = false;
        bool at_boulder = false;
        for (int t = 0; t < 12000 && (g.nodes()[heap].amount > 0 || g.nodes()[boulder].amount > 0); ++t) {
            g.step();
            for (const Villager& v : g.villagers().data()) {
                at_heap = at_heap || (v.job == cutter && v.node == heap + 1 && v.task == Task::Gather);
                at_boulder = at_boulder || (v.job == cutter && v.node == boulder + 1 && v.task == Task::Gather);
            }
        }
        CHECK(at_heap);
        CHECK(at_boulder);
        CHECK(g.nodes()[heap].amount == 0);
        CHECK(g.nodes()[boulder].amount == 0);
        run(g, 1500);
        // What it dug is in its store, in the town's or on the way.
        std::int32_t held = 0;
        for (const Building& b : g.buildings().data()) {
            for (const Stock& s : b.stock) {
                held += s.resource == g.content().find_resource("core:stone") ? s.amount : 0;
            }
        }
        for (const Villager& v : g.villagers().data()) {
            held += v.carrying.resource == g.content().find_resource("core:stone") ? v.carrying.amount : 0;
        }
        CHECK(held >= had + 6 + 40);
    }

    TEST_CASE("every start has loose stones at hand, and the map of before is where it was") {
        // (The counts and hashes are of generator 9: taken with this phase's
        // loose stones switched off.)
        const struct {
            std::uint64_t seed;
            MapSize size;
            std::uint8_t players;
            Sea sea;
            std::uint32_t features;
            std::uint64_t hash;
        } golden[] = {{91, MapSize::Small, 1, Sea::None, 2090, 1175993020570447320ull},
                      {92, MapSize::Small, 1, Sea::None, 1077, 3913821696995622915ull},
                      {2026, MapSize::Medium, 4, Sea::None, 7911, 4990691082199760203ull},
                      {7, MapSize::Small, 2, Sea::OneSide, 1022, 4177312391547667027ull}};
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
            MESSAGE("seed " << want.seed << ": {" << features << ", " << hash << "ull}, loose stones "
                            << m->features.size() - features);
            CHECK(features == want.features);
            CHECK(hash == want.hash);
            CHECK(m->features.size() - features >= 40);
            for (const StartPosition& start : m->starts) {
                int near = 0;
                for (const MapFeature& f : m->features) {
                    const std::int64_t dx = (f.x - start.x).floor_int(), dz = (f.z - start.z).floor_int();
                    if (f.type != FeatureType::LooseStones) {
                        continue;
                    }
                    near += dx * dx + dz * dz <= worldgen::kStartLooseRadius * worldgen::kStartLooseRadius ? 1 : 0;
                    // None where the town center goes.
                    CHECK(dx * dx + dz * dz > worldgen::kStartClearRadius * worldgen::kStartClearRadius);
                }
                CHECK(near >= worldgen::kStartMinLooseStones);
            }
            // None on the ground of a deposit.
            for (const MapFeature& d : m->features) {
                if (!is_deposit(d.type)) {
                    continue;
                }
                const std::int32_t half = deposit_half_side(d.size);
                for (const MapFeature& f : m->features) {
                    if (f.type == FeatureType::LooseStones) {
                        const bool on_it = std::abs(f.x.floor_int() - d.x.floor_int()) <= half &&
                                           std::abs(f.z.floor_int() - d.z.floor_int()) <= half;
                        CHECK_FALSE(on_it);
                    }
                }
            }
        }
    }

    TEST_CASE("saving and loading keeps a heap half taken and the laborer on its way") {
        Game probe(core(), map_for(92), setup());
        const std::int32_t stored = stone(probe);
        const auto content = stone_house(stored + 4);
        Game g(content, map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 14, tz, false);
        REQUIRE(house.valid());
        const Building at = *g.buildings().get(house);
        const std::uint32_t heap = plant(g, FeatureType::LooseStones, at.x + 10, at.z + 2);
        // Until somebody is at the heap.
        bool picking = false;
        for (int t = 0; t < 6000 && !picking; ++t) {
            g.step();
            for (const Villager& v : g.villagers().data()) {
                picking = picking || (v.node == heap + 1 && v.task == Task::Gather && v.carrying.amount > 0);
            }
        }
        REQUIRE(picking);
        BinaryWriter w;
        g.save(w);
        Game loaded(content, map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, content));
        CHECK(loaded.hash() == g.hash());
        for (int t = 0; t < 6000 && !complete(g, house); ++t) {
            g.step();
            loaded.step();
        }
        CHECK(complete(g, house));
        CHECK(complete(loaded, house));
        CHECK(loaded.hash() == g.hash());
        // Four were wanted: two are left on the heap.
        CHECK(g.nodes()[heap].amount == 2);
        CHECK(loaded.nodes()[heap].amount == 2);
    }

    // Not a test: a saved game with the three rocks in the three stones side
    // by side, and a vault waiting for stone the town does not have. Run it
    // by name:
    //   salvaciudad_tests -ts=stones -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_stones.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with loose stones, boulders and outcrops" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        const auto [tx, tz] = town(g);
        for (std::int32_t i = 0; i < 3; ++i) {
            plant(g, FeatureType::LooseStones, tx + 24 + 5 * i, tz - 10);
            plant(g, FeatureType::Stone, tx + 24 + 6 * i, tz - 4);
        }
        Command c;
        c.type = CommandType::DevFeature;
        c.def = static_cast<std::uint16_t>(FeatureType::StoneDeposit);
        c.value = Fixed::one().raw();
        for (std::uint8_t size = 0; size < kDepositSizes; ++size) {
            c.count = size;
            c.position = {Fixed::from_int(tx + 26 + 12 * size), Fixed::from_int(tz + 8)};
            g.apply(c);
        }
        // A vault asks for twice the stone a town starts with: the rest is picked up.
        REQUIRE(put(g, "core:vault", tx + 14, tz - 12, false).valid());
        save::SaveData data;
        data.header.name = "stones";
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
        REQUIRE(save::write_file(folder / "manual_stones.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << ")");
    }
}
