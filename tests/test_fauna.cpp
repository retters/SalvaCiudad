#include <doctest.h>

#include <array>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "core/file_io.h"
#include "game/ambient_fauna.h"
#include "render/model.h"
#include "render/scene_renderer.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

using fauna::Site;
using fauna::Species;
using fauna::When;

When at(sim::Season season, bool night = false, bool snow = false) {
    When w;
    w.season = season;
    w.night = night;
    w.snow = snow;
    return w;
}

// Who lives in a thousand squares like `site`, by species.
std::array<int, fauna::kSpecies> census(const Site& site, const When& when) {
    std::array<int, fauna::kSpecies> out{};
    for (std::uint32_t roll = 0; roll < 1000; ++roll) {
        if (const auto who = fauna::resident(site, when, roll, roll * 7u + 3u)) {
            ++out[static_cast<std::size_t>(*who)];
        }
    }
    return out;
}

int of(const std::array<int, fauna::kSpecies>& c, Species s) {
    return c[static_cast<std::size_t>(s)];
}

int small_birds(const std::array<int, fauna::kSpecies>& c) {
    return of(c, Species::Sparrow) + of(c, Species::Bluebird) + of(c, Species::Robin);
}

int total(const std::array<int, fauna::kSpecies>& c) {
    int n = 0;
    for (const int k : c) {
        n += k;
    }
    return n;
}

}  // namespace

TEST_SUITE("fauna") {
    TEST_CASE("the same square at the same time has the same animal") {
        Site wood;
        wood.tree = true;
        wood.terrain = sim::Terrain::ForestFloor;
        for (std::uint32_t roll = 0; roll < 1000; roll += 37) {
            const auto a = fauna::resident(wood, at(sim::Season::Summer), roll, 5);
            const auto b = fauna::resident(wood, at(sim::Season::Summer), roll, 5);
            CHECK(a == b);
        }
        // Most squares have nobody: the animals are a few, not a crowd.
        CHECK(total(census(wood, at(sim::Season::Summer))) < 400);
        CHECK(total(census(wood, at(sim::Season::Summer))) > 100);
    }

    TEST_CASE("each kind lives where and when it should") {
        Site wood;
        wood.tree = true;
        wood.terrain = sim::Terrain::ForestFloor;
        Site meadow;
        meadow.terrain = sim::Terrain::Meadow;
        meadow.flowers = 60;
        Site bare;
        bare.terrain = sim::Terrain::Rock;
        Site lake;
        lake.water = true;
        Site shore;
        shore.fresh_shore = true;
        const When day = at(sim::Season::Summer);
        const When night = at(sim::Season::Summer, true);

        // Squirrels by day among the trees, both coats; none on a treeless meadow, none under snow.
        const auto in_wood = census(wood, day);
        CHECK(of(in_wood, Species::Squirrel) > 0);
        CHECK(of(in_wood, Species::SquirrelGray) > 0);
        CHECK(of(census(meadow, day), Species::Squirrel) + of(census(meadow, day), Species::SquirrelGray) == 0);
        const auto snowy_wood = census(wood, at(sim::Season::Winter, false, true));
        CHECK(of(snowy_wood, Species::Squirrel) + of(snowy_wood, Species::SquirrelGray) == 0);

        // Owls only at night, in trees; the snowy one where it is cold or white.
        CHECK(of(in_wood, Species::Owl) + of(in_wood, Species::OwlSnowy) == 0);
        const auto wood_at_night = census(wood, night);
        CHECK(of(wood_at_night, Species::Owl) > 0);
        CHECK(of(wood_at_night, Species::OwlSnowy) == 0);
        CHECK(of(census(meadow, night), Species::Owl) == 0);
        Site cold_wood = wood;
        cold_wood.cold = true;
        CHECK(of(census(cold_wood, night), Species::OwlSnowy) > 0);
        CHECK(of(census(cold_wood, night), Species::Owl) == 0);
        // At night nobody else is about, but for fireflies in summer.
        CHECK(small_birds(wood_at_night) == 0);
        CHECK(of(wood_at_night, Species::Squirrel) == 0);
        CHECK(of(wood_at_night, Species::Fireflies) > 0);
        CHECK(of(census(wood, at(sim::Season::Spring, true)), Species::Fireflies) == 0);
        CHECK(of(in_wood, Species::Fireflies) == 0);

        // Butterflies by day over the flowers, from spring to summer.
        CHECK(of(census(meadow, day), Species::Butterflies) > 0);
        CHECK(of(census(meadow, at(sim::Season::Autumn)), Species::Butterflies) == 0);
        CHECK(of(census(meadow, night), Species::Butterflies) == 0);
        Site plain = meadow;
        plain.flowers = 0;
        CHECK(of(census(plain, day), Species::Butterflies) == 0);

        // Dragonflies by fresh water in the warm months.
        CHECK(of(census(shore, day), Species::Dragonflies) > 0);
        CHECK(of(census(shore, at(sim::Season::Winter)), Species::Dragonflies) == 0);
        CHECK(of(census(meadow, day), Species::Dragonflies) == 0);

        // Nobody lives on the water, and bare rock is empty.
        CHECK(total(census(lake, day)) == 0);
        CHECK(total(census(lake, night)) == 0);
        CHECK(total(census(bare, day)) == 0);
    }

    TEST_CASE("the small birds leave in autumn, the robin stays, and gardens draw them") {
        Site wood;
        wood.tree = true;
        Site garden;
        garden.garden = true;
        garden.built = true;
        for (const Site& site : {wood, garden}) {
            const auto spring = census(site, at(sim::Season::Spring));
            const auto summer = census(site, at(sim::Season::Summer));
            const auto autumn = census(site, at(sim::Season::Autumn));
            const auto winter = census(site, at(sim::Season::Winter, false, true));
            CHECK(of(spring, Species::Sparrow) > 0);
            CHECK(of(spring, Species::Bluebird) > 0);
            CHECK(of(summer, Species::Sparrow) > 0);
            CHECK(of(autumn, Species::Sparrow) + of(autumn, Species::Bluebird) == 0);
            CHECK(of(winter, Species::Sparrow) + of(winter, Species::Bluebird) == 0);
            CHECK(of(autumn, Species::Robin) > 0);
            CHECK(of(winter, Species::Robin) > 0);
            CHECK(small_birds(spring) > small_birds(winter));
        }
        // A garden has many more birds than the same ground without it, and butterflies of its own.
        CHECK(small_birds(census(garden, at(sim::Season::Spring))) > 3 * small_birds(census(wood, at(sim::Season::Spring))));
        CHECK(of(census(garden, at(sim::Season::Summer)), Species::Butterflies) > 0);
        // But no squirrels or foxes: it is not the wild.
        const auto in_garden = census(garden, at(sim::Season::Summer));
        CHECK(of(in_garden, Species::Squirrel) + of(in_garden, Species::Fox) == 0);
    }

    TEST_CASE("foxes are few, keep away from buildings, and are white where it is cold") {
        Site meadow;
        meadow.terrain = sim::Terrain::Meadow;
        const auto wild = census(meadow, at(sim::Season::Summer));
        CHECK(of(wild, Species::Fox) > 0);
        CHECK(of(wild, Species::Fox) <= 15);
        CHECK(of(wild, Species::FoxArctic) == 0);
        Site town = meadow;
        town.built = true;
        CHECK(of(census(town, at(sim::Season::Summer)), Species::Fox) == 0);
        Site north = meadow;
        north.cold = true;
        CHECK(of(census(north, at(sim::Season::Summer)), Species::FoxArctic) > 0);
        CHECK(of(census(north, at(sim::Season::Summer)), Species::Fox) == 0);
        CHECK(of(census(meadow, at(sim::Season::Winter, false, true)), Species::FoxArctic) > 0);
    }

    TEST_CASE("where somebody died: a raven and crows, or vultures where it is dry; for a month") {
        CHECK(fauna::carrion_bird(false, 0) == Species::Raven);
        CHECK(fauna::carrion_bird(false, 1) == Species::Crow);
        CHECK(fauna::carrion_bird(false, 2) == Species::Crow);
        for (std::size_t bird = 0; bird < fauna::kCarrionBirds; ++bird) {
            CHECK(fauna::carrion_bird(true, bird) == Species::Vulture);
        }
        CHECK(fauna::kCarrionTicks == 10 * sim::kTicksPerDay);
        // They are never residents of a square: only deaths bring them.
        Site any;
        any.tree = true;
        any.garden = true;
        for (const When& when : {at(sim::Season::Summer), at(sim::Season::Summer, true), at(sim::Season::Winter, false, true)}) {
            const auto c = census(any, when);
            CHECK(of(c, Species::Crow) + of(c, Species::Raven) + of(c, Species::Vulture) == 0);
        }
    }

    TEST_CASE("how each lives, and how far they show") {
        CHECK(fauna::habit(Species::Squirrel) == fauna::Habit::Ground);
        CHECK(fauna::habit(Species::FoxArctic) == fauna::Habit::Ground);
        CHECK(fauna::habit(Species::Owl) == fauna::Habit::Perched);
        CHECK(fauna::habit(Species::Robin) == fauna::Habit::Bird);
        CHECK(fauna::habit(Species::Vulture) == fauna::Habit::Bird);
        CHECK(fauna::habit(Species::Fireflies) == fauna::Habit::Swarm);
        CHECK(fauna::reach(0) == 0.0f);
        CHECK(fauna::reach(1) > 0.0f);
        CHECK(fauna::reach(3) > fauna::reach(1));
        CHECK(fauna::reach(7) == fauna::reach(3));
    }

    TEST_CASE("every animal has its model: rigged, with the clips of its habit, and only fireflies shine") {
        // The limit is that of an animal in art/blender/proposals/game.json.
        const std::filesystem::path core = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods" / "core";
        for (std::size_t k = 0; k < fauna::kSpecies; ++k) {
            const auto species = static_cast<Species>(k);
            const std::string file(fauna::model_file(species));
            const auto bytes = fs::read_file(core / file, render::model_limits::kMaxFileBytes);
            REQUIRE_MESSAGE(bytes.error == fs::IoError::None, file);
            const render::ModelLoadResult r =
                render::load_glb({reinterpret_cast<const std::uint8_t*>(bytes.data.data()), bytes.data.size()});
            REQUIRE_MESSAGE(r.ok, file << ": " << r.error);
            const render::ModelData& m = r.model;
            CHECK_MESSAGE(m.indices.size() / 3 <= 2000u, file << ": " << m.indices.size() / 3);
            CHECK_MESSAGE(m.skinned(), file);
            CHECK_MESSAGE(m.joint_names.size() <= render::model_limits::kMaxJoints, file);
            const fauna::Habit how = fauna::habit(species);
            if (how == fauna::Habit::Swarm) {
                CHECK_MESSAGE(m.clip_index("fly") >= 0, file);
            } else {
                CHECK_MESSAGE(m.clip_index("idle") >= 0, file);
                CHECK_MESSAGE(m.clip_index("walk") >= 0, file);
                CHECK_MESSAGE(m.clip_index("run") >= 0, file);
                CHECK_MESSAGE(m.clip_index("eat") >= 0, file);
            }
            if (how == fauna::Habit::Bird || how == fauna::Habit::Perched) {
                CHECK_MESSAGE(m.clip_index("fly") >= 0, file);
            }
            bool shines = false;
            for (const render::ModelMaterial& mat : m.materials) {
                shines = shines || render::material_glow(mat.name) > 0.0f;
            }
            CHECK_MESSAGE(shines == (species == Species::Fireflies), file);
        }
    }

    TEST_CASE("the animals of the view never touch the game") {
        // They are not in the simulation: asking who lives where, for any time,
        // leaves the game and its map as they were.
        sim::MapSettings s;
        s.seed = 11;
        s.size = sim::MapSize::Small;
        auto map = sim::generate_map(s, test::core_content());
        REQUIRE(map.has_value());
        sim::GameSetup setup;
        setup.seed = 5;
        sim::Game game(std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &test::core_content()), *map,
                       setup);
        for (int i = 0; i < 50; ++i) {
            game.step();
        }
        const std::uint64_t before = game.hash();
        const std::uint64_t checksum = game.map().checksum();
        fauna::AmbientFauna animals;  // Without models it draws nothing, and still must not disturb.
        std::vector<render::CharacterInstance> out;
        animals.note_death(game, 100.0f, 100.0f);
        animals.update(game, {100.0f, 0.0f, 100.0f}, 3, 0.1f, out);
        CHECK(out.empty());
        const When now = fauna::when(game);
        CHECK(now.season == game.calendar().season);
        CHECK(game.hash() == before);
        CHECK(game.map().checksum() == checksum);
    }
}
