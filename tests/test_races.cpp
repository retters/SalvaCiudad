#include <doctest.h>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <ostream>
#include <set>

#include "game/save_file.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"
#include "version.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

const MapData& map_for(std::uint64_t seed) {
    static std::map<std::uint64_t, MapData> cache;
    auto it = cache.find(seed);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        std::optional<MapData> m = generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(seed, std::move(*m)).first;
    }
    return it->second;
}

std::uint8_t race_index(const char* id) {
    const auto& races = sc::test::core_content().races;
    for (std::size_t i = 0; i < races.size(); ++i) {
        if (races[i].id == id) {
            return static_cast<std::uint8_t>(i);
        }
    }
    FAIL("no race " << id);
    return 0;
}

GameSetup setup(std::uint8_t race, std::uint8_t others = 0) {
    GameSetup s;
    s.seed = 19;
    s.rules.climate.seasons = 0b0010;
    s.rules.fires = Threat::None;
    s.rules.diseases = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    s.rules.races.fill(race);
    s.rules.other_races = others;
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

}  // namespace

TEST_SUITE("races") {
    TEST_CASE("core has nine peoples, four of them with traits of their own") {
        const Content& c = sc::test::core_content();
        REQUIRE(c.races.size() == 9);
        const RaceDef& dwarf = c.races[race_index("core:dwarf")];
        const RaceDef& elf = c.races[race_index("core:elf")];
        const RaceDef& cat = c.races[race_index("core:catfolk")];
        const RaceDef& human = c.races[race_index("core:human")];
        const auto work = [](const RaceDef& r, Skill s) { return r.work[static_cast<std::size_t>(s)]; };
        CHECK(work(dwarf, Skill::Stone) > work(human, Skill::Stone));
        CHECK(work(dwarf, Skill::Metal) > work(human, Skill::Metal));
        CHECK(work(elf, Skill::Orchard) > work(human, Skill::Orchard));
        CHECK(work(elf, Skill::Hunt) > work(human, Skill::Hunt));
        CHECK(cat.move > human.move);
        CHECK(cat.night_vision);
        CHECK(dwarf.cold > 0);
        CHECK(elf.disease > 0);
        // Their characters (phase 57): several for the humans, a man and a
        // woman for the dwarves, one for everybody among the catfolk.
        CHECK(human.bodies_male.size() == 4);
        CHECK(human.bodies_female.size() == 4);
        CHECK(dwarf.bodies_male == std::vector<std::string>{"dwarf_man"});
        CHECK(dwarf.bodies_female == std::vector<std::string>{"dwarf_woman"});
        CHECK(cat.bodies_male == std::vector<std::string>{"catfolk"});
        CHECK(cat.bodies_female.empty());
        CHECK_FALSE(human.skins.empty());
        CHECK_FALSE(human.hairs.empty());
        // The new peoples work and walk like the humans.
        for (const char* id : {"core:dark_elf", "core:foxfolk", "core:frogfolk", "core:lizardfolk", "core:orc"}) {
            const RaceDef& r = c.races[race_index(id)];
            CHECK(r.move == human.move);
            CHECK(r.work == human.work);
            CHECK(r.cold == human.cold);
            CHECK(r.disease == human.disease);
            CHECK_FALSE(r.bodies_male.empty());
        }
    }

    TEST_CASE("the rules keep each player's people") {
        GameRules r;
        r.races = {1, 2, 3, kMixedRace, 0, 0, 0, 0, 0, 0, 0, 0};
        r.other_races = 50;
        BinaryWriter w;
        r.write(w);
        GameRules back;
        BinaryReader rd(w.bytes());
        REQUIRE(GameRules::read(rd, back));
        CHECK(back.races == r.races);
        CHECK(back.other_races == 50);
    }

    TEST_CASE("a town starts with its people, or a mix") {
        const std::uint8_t dwarf = race_index("core:dwarf");
        Game g(core(), map_for(191), setup(dwarf));
        for (const Villager& v : g.villagers().data()) {
            CHECK(v.race == dwarf);
        }
        Game mixed(core(), map_for(191), setup(kMixedRace));
        std::set<std::uint8_t> seen;
        for (const Villager& v : mixed.villagers().data()) {
            seen.insert(v.race);
        }
        CHECK(seen.size() >= 4);  // Of the nine peoples, among a dozen villagers.
    }

    TEST_CASE("catfolk walk faster") {
        const auto walked = [](std::uint8_t race) {
            Game g(core(), map_for(192), setup(race));
            run(g, 1);
            // How far all villagers moved in a while.
            double total = 0.0;
            std::map<std::uint32_t, FixedVec2> before;
            for (std::size_t k = 0; k < g.villagers().size(); ++k) {
                before[g.villagers().entities()[k].index] = g.villagers().data()[k].position;
            }
            for (int t = 0; t < 200; ++t) {
                g.step();
                for (std::size_t k = 0; k < g.villagers().size(); ++k) {
                    const Villager& v = g.villagers().data()[k];
                    total += static_cast<double>((v.position - v.previous).length().raw()) / 65536.0;
                }
            }
            return total;
        };
        const double cats = walked(race_index("core:catfolk"));
        const double humans = walked(race_index("core:human"));
        MESSAGE("walked: catfolk " << cats << " m, humans " << humans << " m");
        CHECK(cats > humans * 1.05);
    }

    TEST_CASE("children take a parent's people; newcomers may be of others") {
        const std::uint8_t elf = race_index("core:elf");
        GameSetup s = setup(elf, 100);  // Every newcomer from another people.
        Game g(core(), map_for(193), s);
        const std::size_t races = g.content().races.size();
        // Room and food to attract newcomers.
        const auto grant = [&](const char* id, std::int32_t n) {
            Command c;
            c.type = CommandType::DevGrant;
            c.def = g.content().find_resource(id);
            c.value = n;
            g.apply(c);
        };
        grant("core:log", 400);
        grant("core:stone", 100);
        const DefIndex house = g.content().find_building("core:house");
        const Building* tc = g.buildings().get(g.player(0).town_center);
        const int tx = tc->x;
        const int tz = tc->z;
        int placed = 0;
        for (int r = 12; r < 80 && placed < 5; r += 2) {
            for (int a = 0; a < 8 && placed < 5; ++a) {
                const int x = tx + (a % 3 - 1) * r;
                const int z = tz + (a / 3 - 1) * r;
                if (g.can_place(0, house, x, z, 0) == PlaceError::None) {
                    Command c;
                    c.type = CommandType::PlaceBuilding;
                    c.def = house;
                    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                    g.apply(c);
                    ++placed;
                }
            }
        }
        run(g, 3000);
        grant("core:berries", 3000);
        grant("core:roots", 1000);
        grant("core:fish", 500);
        run(g, 12000);
        bool other = false;
        for (const Villager& v : g.villagers().data()) {
            CHECK(v.race < races);
            other = other || v.race != elf;
        }
        MESSAGE("people " << g.population(0) << ", arrivals " << g.player(0).arrivals << ", births "
                          << g.player(0).births);
        CHECK(g.player(0).arrivals > 0);
        CHECK(other);
        // Without other peoples everyone stays an elf.
        Game pure(core(), map_for(193), setup(elf, 0));
        run(pure, 24000);
        for (const Villager& v : pure.villagers().data()) {
            CHECK(v.race == elf);
        }
    }

    TEST_CASE("races survive a save") {
        Game g(core(), map_for(194), setup(kMixedRace, 50));
        run(g, 1234);
        BinaryWriter w;
        g.save(w);
        Game back(core(), map_for(191), setup(0));
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, core()));
        CHECK(back.hash() == g.hash());
        run(g, 700);
        run(back, 700);
        CHECK(back.hash() == g.hash());
    }

    // Not a test: a saved game of a town of every people, with work for all.
    //   salvasprosperia_tests -ts=races -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_mixed.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a town of every people at work" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        MapSettings ms;
        ms.seed = 92;
        ms.size = MapSize::Small;
        ms.sea = Sea::None;
        std::optional<MapData> map = generate_map(ms, sc::test::core_content());
        REQUIRE(map.has_value());
        GameSetup rules;
        rules.seed = 15;
        rules.rules.fog = FogMode::None;
        rules.rules.diseases = Threat::None;
        rules.rules.fires = Threat::None;
        rules.rules.raiders = Threat::None;
        rules.rules.wildlife = Threat::None;
        Game g(std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content()), *map, rules);
        const auto grant = [&](const char* resource, std::int32_t amount) {
            Command c;
            c.type = CommandType::DevGrant;
            c.def = g.content().find_resource(resource);
            c.value = amount;
            g.apply(c);
        };
        grant("core:bread", 6000);
        grant("core:firewood", 2000);
        // Four grown people of each of the other peoples.
        for (std::size_t r = 0; r < g.content().races.size(); ++r) {
            if (g.content().races[r].id == "core:human") {
                continue;
            }
            Command c;
            c.type = CommandType::DevSpawn;
            c.value = 4;
            c.def2 = static_cast<std::uint16_t>(r + 1);
            g.apply(c);
        }
        const Building tc = *g.buildings().get(g.player(0).town_center);
        const auto put = [&](const char* def, std::int32_t x, std::int32_t z) {
            const DefIndex d = g.content().find_building(def);
            for (std::int32_t r = 0; r <= 20; ++r) {
                for (std::int32_t dz = -r; dz <= r; ++dz) {
                    for (std::int32_t dx = -r; dx <= r; ++dx) {
                        if (std::max(std::abs(dx), std::abs(dz)) == r && g.can_place(0, d, x + dx, z + dz, 0) == PlaceError::None) {
                            Command c;
                            c.type = CommandType::PlaceBuilding;
                            c.def = d;
                            c.position = {Fixed::from_int(x + dx), Fixed::from_int(z + dz)};
                            g.apply(c);
                            Command done;
                            done.type = CommandType::DevBuild;
                            g.apply(done);
                            return;
                        }
                    }
                }
            }
        };
        put("core:storehouse", tc.x - 26, tc.z);
        put("core:woodcutter", tc.x + 18, tc.z - 14);
        put("core:stonecutter", tc.x + 18, tc.z + 12);
        put("core:forager", tc.x - 14, tc.z + 18);
        put("core:hunter", tc.x - 14, tc.z - 20);
        for (int n = 0; n < 6; ++n) {
            put("core:house", tc.x - 24 + n * 10, tc.z - 34);
        }
        for (int t = 0; t < 900; ++t) {
            g.step();
        }
        sc::save::SaveData data;
        data.header.name = "mixed";
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
        REQUIRE(sc::save::write_file(folder / "manual_mixed.scsave", data));
        MESSAGE("a town of " << g.villagers().size() << " people at (" << tc.x << ", " << tc.z << ")");
    }
}
