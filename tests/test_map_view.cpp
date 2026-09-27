#include <doctest.h>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <memory>
#include <thread>

#include "core/file_io.h"
#include "game/dev_tools.h"
#include "game/map_generation.h"
#include "game/map_scene.h"
#include "game/minimap.h"
#include "game/new_game_screen.h"
#include "render/terrain_layer.h"
#include "sim/worldgen.h"
#include "ui/context.h"
#include "ui/font.h"
#include "ui/glyph_atlas.h"
#include "ui/text.h"
#include "test_util.h"

using namespace sc;

namespace {

sim::MapData small_map(std::uint64_t seed) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = sim::MapSize::Small;
    s.players = 2;
    auto m = sim::generate_map(s, sc::test::core_content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

}  // namespace

TEST_SUITE("map_view") {
    TEST_CASE("map visuals match the map") {
        const sim::MapData map = small_map(31);
        const MapVisuals v = build_map_visuals(map, sc::test::core_content());
        CHECK(v.terrain.valid());
        CHECK(v.terrain.cells == 512);
        CHECK(v.terrain.color_size == 512);
        CHECK(v.terrain.heights == map.heights);
        CHECK(v.feature_count() == map.features.size());
        // Every instance stands on the ground under it.
        for (const auto& list : v.features) {
            for (const render::Instance& inst : list) {
                const sim::Fixed x = sim::Fixed::from_raw(static_cast<std::int32_t>(std::lround(inst.position.x * 65536.0f)));
                const sim::Fixed z = sim::Fixed::from_raw(static_cast<std::int32_t>(std::lround(inst.position.z * 65536.0f)));
                const float ground = static_cast<float>(map.height_at(x, z).raw()) / 65536.0f;
                CHECK(std::abs(inst.position.y - ground) < 0.02f);
                CHECK(inst.scale > 0.0f);
            }
        }
        // Same map, same colors.
        const MapVisuals again = build_map_visuals(map, sc::test::core_content());
        CHECK(again.terrain.colors == v.terrain.colors);
    }

    TEST_CASE("huge maps share color texels") {
        render::TerrainData t;
        t.cells = 4096;
        CHECK(std::min(t.cells, kMaxGroundColorSize) == 2048);
    }

    TEST_CASE("terrain data is validated") {
        render::TerrainData t;
        CHECK_FALSE(t.valid());
        t.cells = 64;
        t.heights.assign(65 * 65, 0);
        t.water.assign(64 * 64, 0);
        t.color_size = 64;
        t.colors.assign(64 * 64 * 4, 255);
        CHECK(t.valid());
        t.color_size = 48;  // Not a power of two.
        t.colors.assign(48 * 48 * 4, 255);
        CHECK_FALSE(t.valid());
        t.color_size = 64;
        t.colors.assign(64 * 64 * 4, 255);
        t.cells = 100;  // Not a multiple of a chunk.
        CHECK_FALSE(t.valid());
        t.cells = 64;
        t.heights.pop_back();
        CHECK_FALSE(t.valid());
    }

    TEST_CASE("terrain detail drops with distance") {
        CHECK(render::terrain_lod_for_distance(0.0f) == 0);
        int previous = 0;
        for (float d = 0.0f; d < 5000.0f; d += 25.0f) {
            const int lod = render::terrain_lod_for_distance(d);
            CHECK(lod >= previous);
            CHECK(lod < render::kTerrainLods);
            previous = lod;
        }
        CHECK(previous == render::kTerrainLods - 1);
    }

    TEST_CASE("the camera stands on the ground or the water") {
        const sim::MapData map = small_map(32);
        for (std::int32_t z = 1; z < map.size; z += 37) {
            for (std::int32_t x = 1; x < map.size; x += 41) {
                const float h = map_surface_height(map, static_cast<float>(x) + 0.5f, static_cast<float>(z) + 0.5f);
                const float ground = static_cast<float>(map.height_at(sim::Fixed::from_ratio(2 * x + 1, 2),
                                                                      sim::Fixed::from_ratio(2 * z + 1, 2))
                                                            .raw()) /
                                     65536.0f;
                CHECK(h >= ground - 0.01f);
                if (map.water_at(x, z)) {
                    CHECK(h >= static_cast<float>(map.water[static_cast<std::size_t>(z * map.size + x)]) * 0.01f - 0.01f);
                }
            }
        }
        // Outside the map it takes the edge.
        CHECK(map_surface_height(map, -50.0f, -50.0f) == map_surface_height(map, 0.0f, 0.0f));
    }

    TEST_CASE("ground colors depend on the terrain") {
        const Rgb8 grass = ground_color(sim::Terrain::Grass, 255, 0);
        const Rgb8 dry = ground_color(sim::Terrain::Grass, 0, 0);
        const Rgb8 sand = ground_color(sim::Terrain::Sand, 255, 0);
        CHECK(grass.g > grass.r);
        CHECK(dry.r > grass.r);  // Poor soil looks yellower.
        CHECK(sand.r > grass.r);
    }

    TEST_CASE("generation runs in the background and can be cancelled") {
        MapGenerationJob job;
        sim::MapSettings s;
        s.seed = 77;
        s.size = sim::MapSize::Small;
        job.start(s, std::shared_ptr<const mods::BuildResult>(&sc::test::core_pack(), [](const mods::BuildResult*) {}));
        // Wait for it (small maps take well under a second in release).
        for (int i = 0; i < 6000 && job.status().state == MapGenStatus::State::Running; ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        REQUIRE(job.status().state == MapGenStatus::State::Done);
        CHECK(job.status().overall() == doctest::Approx(1.0f));
        const std::unique_ptr<GeneratedMap> result = job.take();
        REQUIRE(result != nullptr);
        CHECK(result->map.checksum() == sim::generate_map(s, sc::test::core_content())->checksum());
        CHECK(job.status().state == MapGenStatus::State::Idle);
        CHECK(job.take() == nullptr);

        s.size = sim::MapSize::Large;
        job.start(s, std::shared_ptr<const mods::BuildResult>(&sc::test::core_pack(), [](const mods::BuildResult*) {}));
        job.cancel();
        CHECK(job.status().state != MapGenStatus::State::Running);
        CHECK(job.take() == nullptr);
    }
}

TEST_SUITE("dev_tools") {
    TEST_CASE("search folds case and accents") {
        CHECK(fold_for_search("Árbol") == "arbol");
        CHECK(fold_for_search("Fresno de MONTAÑA") == "fresno de montana");
        CHECK(fold_for_search("Pequeño ÉÍÓÚü") == "pequeno eiouu");
        CHECK(fold_for_search("") == "");
        CHECK(fold_for_search("plain 123") == "plain 123");
    }

    TEST_CASE("every tree slot has a model file name") {
        const mods::BuildResult& pack = sc::test::core_pack();
        const sim::Flora& flora = pack.content.flora;
        for (std::size_t s = 0; s < flora.species.size(); ++s) {
            for (std::size_t z = 0; z < sim::kTreeSizes; ++z) {
                const auto size = static_cast<sim::TreeSize>(z);
                if (!flora.species_has_size(s, size)) {
                    continue;
                }
                const std::filesystem::path file =
                    mods::mod_file(pack.dir(flora.species[s].mod), tree_model_file(flora.species[s], size));
                CHECK_MESSAGE(std::filesystem::exists(file), file.string());
            }
        }
    }

    TEST_CASE("grass grows on grass, not on sand") {
        CHECK(grass_density(sim::Terrain::Grass, 255, 200) > 100);
        CHECK(grass_density(sim::Terrain::Sand, 255, 200) == 0);
        CHECK(grass_density(sim::Terrain::Water, 255, 200) == 0);
        CHECK(grass_density(sim::Terrain::Grass, 0, 200) < grass_density(sim::Terrain::Grass, 255, 200));
    }
}

TEST_SUITE("new_game") {
    TEST_CASE("seeds are digits that fit in 64 bits") {
        CHECK(parse_seed("12345") == 12345u);
        CHECK(parse_seed("1") == 1u);
        CHECK(parse_seed("") == 0u);
        CHECK(parse_seed("12a") == 0u);
        CHECK(parse_seed("-5") == 0u);
        CHECK(parse_seed(" 5") == 0u);
        CHECK(parse_seed("9999999999999999999") == 9999999999999999999ull);
        CHECK(parse_seed("99999999999999999999") == 0u);  // 20 digits.
        for (int i = 0; i < 100; ++i) {
            const std::uint64_t s = random_seed();
            CHECK(s >= 1u);
            CHECK(s <= 999'999'999u);
        }
    }

    TEST_CASE("the form generates with its seed, or goes back") {
        auto font = std::make_unique<ui::Font>();
        const auto r = fs::read_file(std::filesystem::path(SC_SOURCE_DIR) / "data/fonts/ui/AlegreyaSans-Regular.ttf",
                                     ui::Font::kMaxFileBytes);
        REQUIRE(font->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end())));
        ui::GlyphAtlas atlas{512};
        ui::TextRenderer text{atlas};
        text.set_font(ui::FontRole::Regular, font.get());
        text.set_font(ui::FontRole::Bold, font.get());
        ui::Context ctx{text};

        NewGameScreen screen;
        screen.open(&sc::test::core_content());
        const auto frame = [&](SDL_Scancode key) {
            ui::Input in;
            if (key != SDL_SCANCODE_UNKNOWN) {
                in.keys.push_back(key);
            }
            ctx.begin_frame(in, 1280, 720, 1.0f, 1'000'000, 0, 0);
            const NewGameScreen::Result result = screen.frame(ctx, false);
            ctx.end_frame();
            return result;
        };
        CHECK(frame(SDL_SCANCODE_UNKNOWN) == NewGameScreen::Result::None);
        CHECK(frame(SDL_SCANCODE_RETURN) == NewGameScreen::Result::Generate);
        CHECK(screen.settings().seed >= 1u);
        CHECK(screen.settings().size == sim::MapSize::Medium);
        CHECK(screen.settings().players == 1);
        CHECK(frame(SDL_SCANCODE_ESCAPE) == NewGameScreen::Result::Back);
    }

    TEST_CASE("the form opens with the last choices, remembers them and resets") {
        const sim::Content& content = sc::test::core_content();
        NewGameSettings last;
        last.size = "giant";
        last.map_type = "core:islands";
        last.biome = "core:pinewood";
        last.islands = 3;
        last.sea = "always";
        last.water = "high";
        last.relief = "gentle";
        last.players = 2;
        last.seasons = 0b1000;
        last.year = "short";
        last.raiders = "brutal";
        last.race = "core:dwarf";
        last.other_races = 50;
        last.max_population = 400;
        NewGameScreen screen;
        screen.open(&content, false, last);
        const sim::MapSettings& m = screen.settings();
        CHECK(m.size == sim::MapSize::Giant);
        CHECK(content.flora.map_types[m.map_type].id == "core:islands");
        CHECK(content.flora.biomes[m.biome].id == "core:pinewood");
        CHECK(m.islands == 3);
        CHECK(m.sea == sim::Sea::Always);
        CHECK(m.water == sim::Amount::High);
        CHECK(m.relief == sim::Relief::Gentle);
        CHECK(m.players == 2);
        CHECK(m.seed >= 1u);
        const sim::GameRules& g = screen.rules();
        CHECK(g.climate.seasons == 0b1000);
        CHECK(g.climate.year == sim::YearLength::Short);
        CHECK(g.raiders == sim::Threat::Brutal);
        CHECK(content.races[g.races[0]].id == "core:dwarf");
        CHECK(g.races[11] == g.races[0]);
        CHECK(g.other_races == 50);
        CHECK(g.max_population == 400);
        // What it remembers opens the same form again.
        const NewGameSettings back = screen.remembered();
        CHECK(back.size == "giant");
        CHECK(back.map_type == "core:islands");
        CHECK(back.race == "core:dwarf");
        NewGameScreen again;
        again.open(&content, false, back);
        CHECK(again.remembered() == back);
        // Reset: the defaults, with the same seed.
        const std::uint64_t seed = screen.settings().seed;
        screen.reset();
        CHECK(screen.settings().seed == seed);
        sim::MapSettings defaults;
        defaults.seed = seed;
        CHECK(screen.settings() == defaults);
        CHECK(screen.rules() == sim::GameRules{});
        // Choices that no longer exist, or seasons the form does not offer, fall back.
        NewGameSettings gone;
        gone.map_type = "oldmod:swamp";
        gone.race = "oldmod:orc";
        gone.seasons = 0b0101;
        gone.max_population = 437;
        NewGameScreen fallback;
        fallback.open(&content, false, gone);
        CHECK(fallback.settings().map_type == 0);
        CHECK(fallback.rules().races[0] == 0);
        CHECK(fallback.rules().climate.seasons == 0b1111);
        CHECK(fallback.rules().max_population == 400);
        NewGameSettings mixed;
        mixed.race = "mixed";
        fallback.open(&content, false, mixed);
        CHECK(fallback.rules().races[0] == sim::kMixedRace);
        CHECK(fallback.remembered().race == "mixed");
    }
}

TEST_SUITE("minimap") {
    TEST_CASE("the compass arrow points north whichever way the camera turns") {
        const auto near = [](std::array<float, 2> v, float x, float y) {
            return std::abs(v[0] - x) < 1e-5f && std::abs(v[1] - y) < 1e-5f;
        };
        const float quarter = 1.5707963f;
        CHECK(near(minimap::north_on_screen(0.0f), 0.0f, -1.0f));        // Looking north: up.
        CHECK(near(minimap::north_on_screen(quarter), -1.0f, 0.0f));     // Looking east: to the left.
        CHECK(near(minimap::north_on_screen(2 * quarter), 0.0f, 1.0f));  // Looking south: down.
        CHECK(near(minimap::north_on_screen(-quarter), 1.0f, 0.0f));     // Looking west: to the right.
    }

    TEST_CASE("the minimap shows the map from above, north up") {
        sim::MapSettings s;
        s.seed = 4;
        s.size = sim::MapSize::Small;
        s.map_type = static_cast<std::uint8_t>(sc::test::core_content().flora.find_map_type("core:islands"));
        s.islands = 1;
        const std::optional<sim::MapData> m = sim::generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        const std::vector<std::uint8_t> img = minimap::render(*m);
        REQUIRE(img.size() == static_cast<std::size_t>(minimap::kImageSize) * minimap::kImageSize * 4);
        const auto texel = [&](int x, int y) { return &img[(static_cast<std::size_t>(y) * minimap::kImageSize + x) * 4]; };
        // The corner is sea: blue. The start is land: green.
        const std::uint8_t* sea = texel(1, 1);
        CHECK(sea[2] > sea[0]);
        CHECK(sea[3] == 255);
        const double per_texel = static_cast<double>(m->size) / minimap::kImageSize;
        const std::uint8_t* home = texel(static_cast<int>(m->starts[0].x.floor_int() / per_texel),
                                         static_cast<int>(m->starts[0].z.floor_int() / per_texel));
        CHECK(home[1] > home[2]);
        CHECK(home[1] > home[0]);
        // The same map, the same picture.
        CHECK(minimap::render(*m) == img);
    }
}
