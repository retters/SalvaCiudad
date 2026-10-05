#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <tuple>
#include <utility>
#include <vector>

#include "game/ground_cover.h"
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

// The base game with shoals of `fish` fish.
std::shared_ptr<const Content> small_shoals(std::int32_t fish) {
    auto c = std::make_shared<Content>(test::core_content());
    for (FeatureDef& f : c->features) {
        if (f.kind == FeatureType::FishShoal) {
            f.amount = fish;
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

// The test map with no shoals, reeds or ducks of its own: the tests put theirs.
MapData bare_map() {
    MapData m = map_for(92);
    std::erase_if(m.features, [](const MapFeature& f) { return f.type >= FeatureType::FishShoal; });
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

// The water nearest to the town, within a walk.
std::pair<std::int32_t, std::int32_t> water_by_town(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    std::int64_t best = INT64_MAX;
    std::pair<std::int32_t, std::int32_t> at{0, 0};
    for (std::int32_t dz = -200; dz <= 200; dz += 2) {
        for (std::int32_t dx = -200; dx <= 200; dx += 2) {
            const std::int32_t x = tc->x + dx, z = tc->z + dz;
            if (x > 4 && z > 4 && x < g.map().size - 4 && z < g.map().size - 4 && g.map().water_at(x, z) &&
                static_cast<std::int64_t>(dx) * dx + static_cast<std::int64_t>(dz) * dz < best) {
                best = static_cast<std::int64_t>(dx) * dx + static_cast<std::int64_t>(dz) * dz;
                at = {x, z};
            }
        }
    }
    REQUIRE(best != INT64_MAX);
    return at;
}

// A fisher's hut by the water nearest to the town, with food for the town and room in its stores.
EntityId hut_by_water(Game& g) {
    grant(g, "core:bread", 4000);
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(put(g, "core:storehouse", tc->x - 26, tc->z).valid());
    const auto [wx, wz] = water_by_town(g);
    const EntityId hut = put(g, "core:fisher", wx, wz);
    REQUIRE(hut.valid());
    return hut;
}

// A feature of `type` on the `n`-th water cell (or, for reeds, land cell) found around the hut, well within its reach.
std::uint32_t plant(Game& g, EntityId hut, FeatureType type, int n) {
    const Building b = at(g, hut);
    const std::int32_t mx = b.x + b.width / 2, mz = b.z + b.depth / 2;
    const bool on_water = type != FeatureType::ReedBank;
    int found = 0;
    for (std::int32_t r = 4; r <= 30; r += 2) {
        for (std::int32_t dz = -r; dz <= r; dz += 2) {
            for (std::int32_t dx = -r; dx <= r; dx += 2) {
                if (std::max(std::abs(dx), std::abs(dz)) != r || dx * dx + dz * dz > 30 * 30 ||
                    g.map().water_at(mx + dx, mz + dz) != on_water) {
                    continue;
                }
                if (found++ < n * 3) {
                    continue;  // A few cells apart.
                }
                Command c;
                c.type = CommandType::DevFeature;
                c.def = static_cast<std::uint16_t>(type);
                c.value = Fixed::one().raw();
                c.position = {Fixed::from_int(mx + dx), Fixed::from_int(mz + dz)};
                const std::size_t before = g.map().features.size();
                g.apply(c);
                REQUIRE(g.map().features.size() == before + 1);
                return static_cast<std::uint32_t>(before);
            }
        }
    }
    FAIL("no place for it by the hut");
    return 0;
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

}  // namespace

TEST_SUITE("fishing") {
    TEST_CASE("the base game has shoals, reeds and ducks, and how much each adds to a fisher's catch") {
        const Content& c = test::core_content();
        const FeatureDef* shoal = c.feature(FeatureType::FishShoal);
        const FeatureDef* reeds = c.feature(FeatureType::ReedBank);
        const FeatureDef* ducks = c.feature(FeatureType::Ducks);
        REQUIRE(shoal != nullptr);
        REQUIRE(reeds != nullptr);
        REQUIRE(ducks != nullptr);
        CHECK(shoal->amount == 40);
        CHECK(shoal->resource == c.find_resource("core:fish"));
        CHECK(ducks->resource == c.find_resource("core:eggs"));
        CHECK_FALSE(is_deposit(FeatureType::FishShoal));
        // Nobody gathers them: they are the fisher's.
        for (const BuildingDef& b : c.buildings) {
            CHECK((b.gathers & (7u << static_cast<unsigned>(FeatureType::FishShoal))) == 0);
        }
        // Half of before alone; a third more for each shoal or bank of reeds; one and a half at most.
        Game::FishSpots spots;
        CHECK(Game::fish_percent(spots) == 50);
        spots.shoals = 1;
        CHECK(Game::fish_percent(spots) == 84);
        spots.reeds = 1;
        CHECK(Game::fish_percent(spots) == 118);
        spots.shoals = 2;
        CHECK(Game::fish_percent(spots) == 150);
        spots.reeds = 4;
        CHECK(Game::fish_percent(spots) == 150);
        spots = {};
        spots.spent = 3;  // Fished out: they add nothing.
        spots.ducks = 2;  // Nor do the ducks.
        CHECK(Game::fish_percent(spots) == 50);
        CHECK_FALSE(cover::model_file(cover::Kind::BeaverDam).empty());
    }

    TEST_CASE("a hut with nothing in its reach fishes half as fast as one with three banks of reeds makes it thrice") {
        const auto catch_in = [](int reeds, std::int32_t& percent) {
            Game g(core(), bare_map(), setup(0b0010));
            const EntityId hut = hut_by_water(g);
            for (int n = 0; n < reeds; ++n) {
                plant(g, hut, FeatureType::ReedBank, n);
            }
            const Game::FishSpots spots = g.fish_spots(at(g, hut));
            CHECK(spots.reeds == reeds);
            CHECK(spots.shoals == 0);
            percent = Game::fish_percent(spots);
            const std::int32_t fish = have(g, "core:fish");
            // The time spent at the water, from the first cast.
            std::int32_t ticks = 0;
            for (std::uint32_t t = 0; t < 6000; ++t) {
                g.step();
                for (const Villager& v : g.villagers().data()) {
                    ticks += v.task == Task::Fish ? 1 : 0;
                }
            }
            const std::int32_t caught = have(g, "core:fish") - fish;
            MESSAGE("with " << reeds << " banks of reeds: " << caught << " fish in " << ticks << " ticks at the water");
            return std::pair{caught, ticks};
        };
        std::int32_t alone_percent = 0, reeds_percent = 0;
        const auto [alone, alone_ticks] = catch_in(0, alone_percent);
        const auto [with, with_ticks] = catch_in(3, reeds_percent);
        CHECK(alone_percent == 50);
        CHECK(reeds_percent == 150);
        REQUIRE(alone > 0);
        REQUIRE(with > 0);
        // Ticks at the water for each fish: 90 alone (45 before), 30 with the three. (They eat some of what they catch.)
        const double each_alone = static_cast<double>(alone_ticks) / alone;
        const double each_with = static_cast<double>(with_ticks) / with;
        CHECK(each_alone > 80.0);
        CHECK(each_with < 45.0);
        CHECK(with > alone);
    }

    TEST_CASE("a shoal fished without rest is fished out, and is back when the season changes") {
        Game g(small_shoals(12), bare_map(), setup());
        REQUIRE(g.calendar().season == Season::Spring);
        const EntityId hut = hut_by_water(g);
        const std::uint32_t shoal = plant(g, hut, FeatureType::FishShoal, 0);
        CHECK(g.nodes()[shoal].amount == 12);
        CHECK(g.fish_spots(at(g, hut)).shoals == 1);
        CHECK(Game::fish_percent(g.fish_spots(at(g, hut))) == 84);
        // (The spring begins with ice: nobody fishes until it is gone.)
        for (std::uint32_t t = 0; t < g.year_ticks() && g.nodes()[shoal].amount > 0; ++t) {
            g.step();
        }
        REQUIRE(g.nodes()[shoal].amount == 0);
        const Season when = g.calendar().season;
        const Game::FishSpots spent = g.fish_spots(at(g, hut));
        CHECK(spent.shoals == 0);
        CHECK(spent.spent == 1);
        CHECK(Game::fish_percent(spent) == 50);
        // It stays empty for the rest of the season, whatever is fished meanwhile.
        while (g.calendar().season == when) {
            g.step();
            if (g.calendar().season == when) {
                CHECK(g.nodes()[shoal].amount == 0);
            }
        }
        // The next one: it is full again (but for what is fished from then on).
        run(g, 2 * g.calendar_day_ticks());
        CHECK(g.nodes()[shoal].amount > 0);
        CHECK(g.fish_spots(at(g, hut)).shoals == 1);
        CHECK(g.fish_spots(at(g, hut)).spent == 0);
    }

    TEST_CASE("with ducks in reach the fishers bring eggs in spring and summer, and meat in autumn") {
        Game g(core(), bare_map(), setup());
        const EntityId hut = hut_by_water(g);
        plant(g, hut, FeatureType::Ducks, 0);
        REQUIRE(g.fish_spots(at(g, hut)).ducks == 1);
        REQUIRE(have(g, "core:eggs") == 0);
        REQUIRE(have(g, "core:meat") == 0);
        bool eggs = false, meat_early = false, meat = false;
        while (g.calendar().season != Season::Autumn) {
            g.step();
            eggs = eggs || have(g, "core:eggs") > 0;
            meat_early = meat_early || have(g, "core:meat") > 0;
        }
        CHECK(eggs);
        CHECK_FALSE(meat_early);
        while (g.calendar().season == Season::Autumn) {
            g.step();
            meat = meat || have(g, "core:meat") > 0;
        }
        CHECK(meat);
        // Without ducks, neither.
        Game plain(core(), bare_map(), setup());
        (void)hut_by_water(plain);
        bool any = false;
        while (plain.calendar().season != Season::Winter) {
            plain.step();
            any = any || have(plain, "core:eggs") > 0 || have(plain, "core:meat") > 0;
        }
        CHECK_FALSE(any);
    }

    TEST_CASE("with ice nobody fishes") {
        Game g(core(), bare_map(), setup());
        const EntityId hut = hut_by_water(g);
        plant(g, hut, FeatureType::ReedBank, 0);
        // (One who was on its way gets to the water, sees the ice and leaves: a tick at most.)
        bool fished = false, froze = false;
        int frozen_ticks = 0;
        std::int32_t at_freeze = 0;
        std::map<std::uint32_t, int> casting;
        for (std::uint32_t t = 0; t < g.year_ticks(); ++t) {
            g.step();
            const bool ice = g.temperature() <= -3;
            frozen_ticks = ice ? frozen_ticks + 1 : 0;
            if (frozen_ticks == 400) {
                at_freeze = have(g, "core:fish");
            }
            if (frozen_ticks > 400 && frozen_ticks % 100 == 0) {
                // Nothing comes in: what there is only goes down (they eat it).
                CHECK(have(g, "core:fish") <= at_freeze);
                froze = true;
            }
            for (std::size_t k = 0; k < g.villagers().size(); ++k) {
                const Villager& v = g.villagers().data()[k];
                fished = fished || v.task == Task::Fish;
                int& ticks = casting[g.villagers().entities()[k].index];
                ticks = ice && v.task == Task::Fish ? ticks + 1 : 0;
                if (frozen_ticks > 5) {
                    CHECK(ticks <= 1);
                }
            }
        }
        CHECK(fished);
        REQUIRE(froze);
    }

    TEST_CASE("every start has a shoal or reeds by the water nearest to it, and none where its town center goes") {
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
            int shoals = 0, reeds = 0, ducks = 0;
            for (const MapFeature& f : m->features) {
                shoals += f.type == FeatureType::FishShoal ? 1 : 0;
                reeds += f.type == FeatureType::ReedBank ? 1 : 0;
                ducks += f.type == FeatureType::Ducks ? 1 : 0;
                if (f.type == FeatureType::FishShoal || f.type == FeatureType::Ducks) {
                    CHECK(m->water_at(f.x.floor_int(), f.z.floor_int()));
                } else if (f.type == FeatureType::ReedBank) {
                    CHECK_FALSE(m->water_at(f.x.floor_int(), f.z.floor_int()));
                }
            }
            MESSAGE("seed " << seed << ": " << shoals << " shoals, " << reeds << " banks of reeds, " << ducks << " ducks");
            CHECK(shoals + reeds > 0);
            for (const StartPosition& start : m->starts) {
                const std::int32_t sx = start.x.floor_int(), sz = start.z.floor_int();
                // The water nearest to it that a shoal fits in, as the generator looks for it.
                std::int64_t best = INT64_MAX;
                std::int32_t bx = 0, bz = 0;
                const std::int32_t r = worldgen::kStartFishRadius;
                for (std::int32_t z = std::max(4, sz - r); z < std::min(m->size - 4, sz + r); z += 2) {
                    for (std::int32_t x = std::max(4, sx - r); x < std::min(m->size - 4, sx + r); x += 2) {
                        const std::int64_t d = static_cast<std::int64_t>(x - sx) * (x - sx) + static_cast<std::int64_t>(z - sz) * (z - sz);
                        const std::int64_t clear = worldgen::kStartClearRadius + 2;
                        if (d < best && d > clear * clear && m->water_at(x, z) && m->water_at(x + 2, z) && m->water_at(x - 2, z) &&
                            m->water_at(x, z + 2) && m->water_at(x, z - 2)) {
                            best = d;
                            bx = x;
                            bz = z;
                        }
                    }
                }
                if (best == INT64_MAX) {
                    MESSAGE("no water within " << r << " m of a start");
                    continue;
                }
                bool near = false;
                for (const MapFeature& f : m->features) {
                    const std::int64_t dx = f.x.floor_int() - bx, dz = f.z.floor_int() - bz;
                    near = near || ((f.type == FeatureType::FishShoal || f.type == FeatureType::ReedBank) &&
                                    dx * dx + dz * dz <= (worldgen::kStartFishNear + 2) * (worldgen::kStartFishNear + 2));
                    if (f.type >= FeatureType::FishShoal) {
                        const std::int64_t tx = f.x.floor_int() - sx, tz = f.z.floor_int() - sz;
                        CHECK(tx * tx + tz * tz > worldgen::kStartClearRadius * worldgen::kStartClearRadius);
                    }
                }
                CHECK(near);
            }
        }
    }

    TEST_CASE("saving and loading keeps a shoal half fished") {
        Game g(core(), bare_map(), setup());
        const EntityId hut = hut_by_water(g);
        const std::uint32_t shoal = plant(g, hut, FeatureType::FishShoal, 0);
        plant(g, hut, FeatureType::Ducks, 1);
        for (std::uint32_t t = 0; t < 3000 && g.nodes()[shoal].amount > 25; ++t) {
            g.step();
        }
        REQUIRE(g.nodes()[shoal].amount <= 25);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), bare_map(), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.nodes()[shoal].amount == g.nodes()[shoal].amount);
        run(g, g.year_ticks() / 3);
        run(loaded, loaded.year_ticks() / 3);
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.nodes()[shoal].amount == g.nodes()[shoal].amount);
    }

    // Not a test: a saved game with a fisher's hut by the water, three shoals,
    // reeds and ducks in its reach. Run it by name:
    //   salvaciudad_tests -ts=fishing -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_fishing.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a fisher among shoals, reeds and ducks" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        const EntityId hut = hut_by_water(g);
        for (int n = 0; n < 3; ++n) {
            plant(g, hut, FeatureType::FishShoal, n);
        }
        plant(g, hut, FeatureType::ReedBank, 0);
        plant(g, hut, FeatureType::ReedBank, 2);
        plant(g, hut, FeatureType::Ducks, 4);
        run(g, 600);
        save::SaveData data;
        data.header.name = "fishing";
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
        REQUIRE(save::write_file(folder / "manual_fishing.scsave", data));
        const Game::FishSpots spots = g.fish_spots(at(g, hut));
        MESSAGE("hut at (" << at(g, hut).x << ", " << at(g, hut).z << "): " << spots.shoals << " shoals, " << spots.reeds
                           << " reeds, " << spots.ducks << " ducks");
    }
}
