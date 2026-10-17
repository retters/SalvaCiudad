#include <doctest.h>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <functional>
#include <memory>
#include <set>
#include <thread>

#include <SDL3/SDL_timer.h>

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
                if (map.water_at(x.floor_int(), z.floor_int())) {
                    // What lives in the water (phase 110): on it, the ducks; or just under it, the fish.
                    const float surface = map_surface_height(map, inst.position.x, inst.position.z);
                    CHECK(inst.position.y <= surface + 0.02f);
                    CHECK(inst.position.y >= surface - 0.5f);
                } else {
                    CHECK(std::abs(inst.position.y - ground) < 0.02f);
                }
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

    TEST_CASE("every tree species has its model files, near and far") {
        const mods::BuildResult& pack = sc::test::core_pack();
        const sim::Flora& flora = pack.content.flora;
        REQUIRE(flora.species.size() >= 27);
        for (const sim::SpeciesDef& sp : flora.species) {
            CHECK_MESSAGE(!sp.state_models[0].empty(), sp.id);
            for (std::size_t st = 0; st < sim::kTreeStates; ++st) {
                REQUIRE(sp.state_far[st].size() == sp.state_models[st].size());
                for (std::size_t i = 0; i < sp.state_models[st].size(); ++i) {
                    for (const std::string& rel : {sp.state_models[st][i], sp.state_far[st][i]}) {
                        const std::filesystem::path file = mods::mod_file(pack.dir(sp.mod), rel);
                        CHECK_MESSAGE(std::filesystem::exists(file), sp.id << ": " << rel);
                    }
                }
                const std::filesystem::path first =
                    mods::mod_file(pack.dir(sp.mod), tree_model_file(sp, static_cast<sim::TreeState>(st)));
                CHECK_MESSAGE(std::filesystem::exists(first), first.string());
            }
        }
        // An evergreen has only its bloom; the others, the three states (a giant, two).
        const auto states = [&](std::string_view id) {
            const int i = flora.find_species(id);
            REQUIRE(i >= 0);
            const sim::SpeciesDef& sp = flora.species[static_cast<std::size_t>(i)];
            return static_cast<int>(!sp.state_models[0].empty()) + static_cast<int>(!sp.state_models[1].empty()) +
                   static_cast<int>(!sp.state_models[2].empty());
        };
        CHECK(states("core:pine") == 1);
        CHECK(states("core:palm") == 1);
        CHECK(states("core:elm") == 3);
        CHECK(states("core:giant_sequoia") == 2);
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
        last.mode = "custom";
        last.size = "giant";
        last.players = 2;
        last.biomes = {"core:boreal"};
        last.sea = "archipelago";
        last.islands = 3;
        last.landforms = 50;
        last.rivers = 200;
        last.relief = 100;
        last.temperature = 50;
        last.climate = "even";
        last.giants_on = false;
        last.seasons = 0b1000;
        last.season_minutes = {3, 4, 5, 9};
        last.raiders = "brutal";
        last.race = "core:dwarf";
        last.other_races = 200;
        last.immigrants = {"core:elf", "core:human"};
        last.max_population = 400;
        last.fog = "dynamic";
        last.shared_vision = false;
        NewGameScreen screen;
        screen.open(&content, false, last);
        CHECK(screen.custom());
        const sim::MapSettings& m = screen.settings();
        CHECK(m.size == sim::MapSize::Giant);
        CHECK(m.island_map());
        CHECK(m.sea == sim::Sea::Archipelago);
        REQUIRE(content.flora.find_biome("core:boreal") >= 0);
        CHECK(m.biomes == std::uint64_t{1} << content.flora.find_biome("core:boreal"));
        CHECK(m.islands == 3);
        CHECK(m.landforms == 50);
        CHECK(m.rivers == 200);
        CHECK(m.lakes == 100);
        CHECK(m.relief == sim::Relief::Gentle);
        CHECK(m.temperature == 50);
        CHECK(m.climate_range < sim::kMaxClimateRange);
        CHECK(m.giants == 0);  // Switched off.
        CHECK(m.players == 2);
        CHECK(m.seed >= 1u);
        const sim::GameRules& g = screen.rules();
        CHECK(g.climate.seasons == 0b1000);
        CHECK(g.climate.minutes == std::array<std::uint8_t, 4>{0, 0, 0, 9});  // Only the winter it has.
        CHECK(sim::year_ticks(g.climate) == 9u * sim::kTicksPerMinute);
        CHECK(g.raiders == sim::Threat::Brutal);
        CHECK(content.races[g.races[0]].id == "core:dwarf");
        CHECK(g.races[11] == g.races[0]);
        CHECK(g.other_races == 40);  // Twice the usual fifth.
        const int elf = [&] {
            for (std::size_t r = 0; r < content.races.size(); ++r) {
                if (content.races[r].id == "core:elf") {
                    return static_cast<int>(r);
                }
            }
            return -1;
        }();
        REQUIRE(elf >= 0);
        CHECK(((g.immigrants >> elf) & 1u) == 1u);
        CHECK(g.immigrants != 0);
        CHECK(g.max_population == 400);
        CHECK(g.fog == sim::FogMode::Dynamic);
        CHECK_FALSE(g.shared_vision);
        // What it remembers opens the same form again.
        const NewGameSettings back = screen.remembered();
        CHECK(back.mode == "custom");
        CHECK(back.size == "giant");
        CHECK(back.sea == "archipelago");
        CHECK(back.race == "core:dwarf");
        CHECK(back.biomes == std::vector<std::string>{"core:boreal"});
        CHECK(back.immigrants.size() == 2);
        NewGameScreen again;
        again.open(&content, false, back);
        CHECK(again.remembered() == back);
        // Choices that no longer exist fall back; none left of a list means all.
        NewGameSettings gone;
        gone.mode = "custom";
        gone.biomes = {"oldmod:swamp"};
        gone.race = "oldmod:orc";
        gone.immigrants = {"oldmod:orc"};
        gone.seasons = 0b0101;
        gone.max_population = 437;
        gone.rivers = 60;  // Not on a step.
        NewGameScreen fallback;
        fallback.open(&content, false, gone);
        CHECK_FALSE(fallback.settings().island_map());
        CHECK(fallback.settings().biomes == 0);  // Every biome.
        CHECK(fallback.settings().rivers == 50);
        CHECK(fallback.rules().races[0] == sim::kMixedRace);  // The form's default.
        CHECK(fallback.rules().immigrants == 0);
        CHECK(fallback.rules().climate.seasons == 0b0101);  // Every season by itself now.
        CHECK(fallback.rules().max_population == 400);
        NewGameSettings mixed;
        mixed.mode = "custom";
        mixed.race = "mixed";
        fallback.open(&content, false, mixed);
        CHECK(fallback.rules().races[0] == sim::kMixedRace);
        CHECK(fallback.remembered().race == "mixed");
    }

    TEST_CASE("varied: the seed chooses the climate and the sea, the rest is the usual") {
        // The same seed, the same choices.
        const sim::MapSettings a = varied_map(77, sim::MapSize::Medium, 2);
        CHECK(a == varied_map(77, sim::MapSize::Medium, 2));
        CHECK(a.seed == 77u);
        CHECK(a.size == sim::MapSize::Medium);
        CHECK(a.players == 2);
        // The usual in everything else.
        const sim::MapSettings usual;
        CHECK(a.rivers == usual.rivers);
        CHECK(a.lakes == usual.lakes);
        CHECK(a.forests == usual.forests);
        CHECK(a.resources == usual.resources);
        CHECK(a.relief == sim::Relief::Gentle);
        CHECK(a.landforms == usual.landforms);
        CHECK(a.giants == 100);
        CHECK(a.biomes == 0);
        const sim::GameRules rules = varied_rules();
        CHECK(rules.climate.seasons == 0b1111);
        CHECK(rules.climate.year == sim::YearLength::Normal);
        CHECK(sim::year_ticks(rules.climate) == sim::year_ticks(sim::YearLength::Normal));
        CHECK(rules.fog == sim::FogMode::None);
        CHECK(rules.shared_vision);
        CHECK(rules.max_population == 1000);
        CHECK(rules.races[0] == sim::kMixedRace);
        CHECK(rules.other_races == 20);
        CHECK(rules.diseases == sim::Threat::Medium);
        // Over many seeds: every climate and every kind of sea.
        std::set<VariedClimate> climates;
        std::set<sim::Sea> seas;
        for (std::uint64_t seed = 1; seed <= 300; ++seed) {
            const sim::MapSettings s = varied_map(seed, sim::MapSize::Large, 1);
            climates.insert(varied_climate(seed));
            seas.insert(s.sea);
            CHECK(s.islands >= 1);
            CHECK((s.climate_range == sim::kMaxClimateRange) == (varied_climate(seed) == VariedClimate::Mixed));
        }
        CHECK(climates.size() == static_cast<std::size_t>(VariedClimate::Count));
        CHECK(seas.size() == static_cast<std::size_t>(sim::Sea::Count));
    }

    TEST_CASE("custom from varied gives the map varied gives") {
        const sim::Content& content = sc::test::core_content();
        NewGameSettings last;
        last.size = "small";
        NewGameScreen varied;
        varied.open(&content, false, last);
        CHECK_FALSE(varied.custom());
        const sim::MapSettings v = varied.settings();
        CHECK(v == varied_map(v.seed, sim::MapSize::Small, 1));
        CHECK(varied.rules() == varied_rules());
        // The same seed in a custom form filled from varied.
        auto font = std::make_unique<ui::Font>();
        const auto r = fs::read_file(std::filesystem::path(SC_SOURCE_DIR) / "data/fonts/ui/AlegreyaSans-Regular.ttf",
                                     ui::Font::kMaxFileBytes);
        REQUIRE(font->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end())));
        ui::GlyphAtlas atlas{512};
        ui::TextRenderer text{atlas};
        text.set_font(ui::FontRole::Regular, font.get());
        text.set_font(ui::FontRole::Bold, font.get());
        ui::Context ctx{text};
        std::uint64_t now = 1'000'000;
        const auto frame = [&](NewGameScreen& screen) {
            ui::Input in;
            now += 100'000'000;  // A tenth of a second.
            ctx.begin_frame(in, 1280, 720, 1.0f, now, 0, 0);
            const NewGameScreen::Result result = screen.frame(ctx, false);
            ctx.end_frame();
            return result;
        };
        varied.start_from_varied();
        CHECK(frame(varied) == NewGameScreen::Result::None);
        CHECK(varied.custom());
        CHECK(varied.settings() == v);
        CHECK(varied.rules() == varied_rules());
        const auto a = sim::generate_map(v, content);
        const auto b = sim::generate_map(varied.settings(), content);
        REQUIRE(a.has_value());
        REQUIRE(b.has_value());
        CHECK(a->checksum() == b->checksum());
        // The preview: a picture of the map a moment after the form settles.
        std::optional<std::vector<std::uint8_t>> image;
        for (int i = 0; i < 400 && !image; ++i) {
            (void)frame(varied);
            image = varied.take_preview();
            if (!image) {
                SDL_Delay(10);
            }
        }
        REQUIRE(image.has_value());
        CHECK(image->size() == static_cast<std::size_t>(minimap::kImageSize) * minimap::kImageSize * 4u);
        CHECK(image->size() == minimap::render(*a).size());
        CHECK(*image == minimap::render(*a));
        CHECK_FALSE(varied.take_preview().has_value());  // Once.
        varied.close();
    }

    TEST_CASE("the custom form scrolls down to its buttons") {
        const sim::Content& content = sc::test::core_content();
        NewGameSettings last;
        last.size = "small";
        last.mode = "custom";
        NewGameScreen screen;
        screen.open(&content, false, last);
        REQUIRE(screen.custom());
        auto font = std::make_unique<ui::Font>();
        const auto r = fs::read_file(std::filesystem::path(SC_SOURCE_DIR) / "data/fonts/ui/AlegreyaSans-Regular.ttf",
                                     ui::Font::kMaxFileBytes);
        REQUIRE(font->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end())));
        ui::GlyphAtlas atlas{512};
        ui::TextRenderer text{atlas};
        text.set_font(ui::FontRole::Regular, font.get());
        text.set_font(ui::FontRole::Bold, font.get());
        ui::Context ctx{text};
        std::uint64_t now = 1'000'000;
        const auto frame = [&](const ui::Input& in) {
            now += 16'000'000;
            ctx.begin_frame(in, 1280, 720, 1.0f, now, 0, 0);
            const NewGameScreen::Result result = screen.frame(ctx, false);
            ctx.end_frame();
            return result;
        };
        // "Generate" ends up at the bottom right of the panel, 680 wide and
        // centered: out of sight until the form is scrolled all the way.
        ui::Input at;
        at.mouse_x = 856.0f;
        at.mouse_y = 656.0f;
        const auto click = [&] {
            ui::Input down = at;
            down.mouse_down = down.mouse_pressed = true;
            ui::Input up = at;
            up.mouse_released = true;
            const NewGameScreen::Result first = frame(down);
            const NewGameScreen::Result second = frame(up);
            return first != NewGameScreen::Result::None ? first : second;
        };
        CHECK(frame(at) == NewGameScreen::Result::None);
        const sim::MapSettings before = screen.settings();
        ui::Input wheel = at;
        wheel.wheel = -3.0f;
        for (int i = 0; i < 40; ++i) {
            CHECK(frame(wheel) == NewGameScreen::Result::None);
        }
        CHECK(screen.settings() == before);  // The wheel changes no choice.
        CHECK(click() == NewGameScreen::Result::Generate);
        screen.close();
    }

    TEST_CASE("the custom choices change the map as they say") {
        const sim::Content& content = sc::test::core_content();
        const auto make = [&](const std::function<void(sim::MapSettings&)>& change) {
            sim::MapSettings s;
            s.seed = 404;
            s.size = sim::MapSize::Medium;
            change(s);
            std::optional<sim::MapData> m = sim::generate_map(s, content);
            REQUIRE(m.has_value());
            return std::move(*m);
        };
        const auto count = [](const sim::MapData& m, sim::FeatureType type) {
            return std::count_if(m.features.begin(), m.features.end(), [&](const sim::MapFeature& f) { return f.type == type; });
        };
        const auto water = [](const sim::MapData& m) {
            return std::count_if(m.water.begin(), m.water.end(), [](std::uint16_t w) { return w != 0; });
        };
        const sim::MapData usual = make([](sim::MapSettings&) {});
        // Forests: none, the usual, many.
        const sim::MapData bare = make([](sim::MapSettings& s) { s.forests = 0; s.giants = 0; });
        const sim::MapData thick = make([](sim::MapSettings& s) { s.forests = 200; });
        CHECK(count(bare, sim::FeatureType::Tree) < count(usual, sim::FeatureType::Tree) / 10);
        CHECK(count(thick, sim::FeatureType::Tree) > count(usual, sim::FeatureType::Tree) * 12 / 10);
        // Resources.
        const sim::MapData poor = make([](sim::MapSettings& s) { s.resources = 25; });
        const sim::MapData rich = make([](sim::MapSettings& s) { s.resources = 200; });
        CHECK(count(poor, sim::FeatureType::Stone) < count(usual, sim::FeatureType::Stone));
        CHECK(count(rich, sim::FeatureType::Stone) > count(usual, sim::FeatureType::Stone));
        // Rivers and lakes: more water with more of them, less with none.
        const sim::MapData dry = make([](sim::MapSettings& s) { s.rivers = 0; s.lakes = 0; });
        const sim::MapData wet = make([](sim::MapSettings& s) { s.rivers = 200; s.lakes = 200; });
        CHECK(water(dry) < water(usual));
        CHECK(water(wet) > water(usual));
        // Relief: the highest ground rises with it.
        const auto top = [](const sim::MapData& m) { return *std::max_element(m.heights.begin(), m.heights.end()); };
        const sim::MapData flat = make([](sim::MapSettings& s) { s.relief = 0; });
        const sim::MapData steep = make([](sim::MapSettings& s) { s.relief = 200; });
        CHECK(top(flat) < top(steep));
        // The sea: none, a side, islands.
        const auto salt = [](const sim::MapData& m) { return !m.sea_levels.empty() && m.sea_levels[0] != 0; };
        CHECK_FALSE(salt(usual));
        CHECK(salt(make([](sim::MapSettings& s) { s.sea = sim::Sea::OneSide; })));
        CHECK(salt(make([](sim::MapSettings& s) { s.sea = sim::Sea::TwoSides; })));
        const sim::MapData islands = make([](sim::MapSettings& s) { s.sea = sim::Sea::Islands; s.players = 2; });
        CHECK(salt(islands));
        CHECK(water(islands) > water(usual) * 3);
        // Giants: none when switched off.
        const auto giants = [&](const sim::MapData& m) {
            return std::count_if(m.features.begin(), m.features.end(), [&](const sim::MapFeature& f) {
                return f.type == sim::FeatureType::Tree && content.flora.species[f.species].giant_biome >= 0;
            });
        };
        CHECK(giants(make([](sim::MapSettings& s) { s.giants = 0; })) == 0);
        CHECK(giants(make([](sim::MapSettings& s) { s.giants = 200; })) >= giants(usual));
        // A map of one climate: cold has no savanna, warm has no boreal forest.
        const auto share = [&](const sim::MapData& m, const char* id) {
            const int b = content.flora.find_biome(id);
            REQUIRE(b >= 0);
            return std::count(m.biome.begin(), m.biome.end(), static_cast<std::uint8_t>(b)) * 100 /
                   static_cast<std::ptrdiff_t>(m.biome.size());
        };
        const sim::MapData cold = make([](sim::MapSettings& s) { s.temperature = 25; s.climate_range = 12; });
        const sim::MapData warm = make([](sim::MapSettings& s) { s.temperature = 175; s.climate_range = 12; });
        CHECK(share(cold, "core:savanna") == 0);
        CHECK(share(warm, "core:boreal") == 0);
        CHECK(share(cold, "core:boreal") + share(cold, "core:mountain") > 50);
        // The year without winter, and its length.
        sim::GameRules rules;
        rules.climate.seasons = 0b0111;
        rules.climate.year = 50;
        for (std::uint64_t tick = 0; tick < sim::year_ticks(50) * 2; tick += 100) {
            CHECK(sim::calendar(rules.climate, tick).season != sim::Season::Winter);
        }
        CHECK(sim::year_ticks(50) * 2 == sim::year_ticks(100));
        CHECK(sim::year_ticks(200) == sim::year_ticks(100) * 2);
        CHECK(sim::year_ticks(25) % 120 == 0);
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
        s.sea = sc::sim::Sea::Archipelago;
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
