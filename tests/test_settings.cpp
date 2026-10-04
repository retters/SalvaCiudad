#include <doctest.h>

#include "game/settings.h"
#include "test_util.h"

using namespace sc;

namespace {

SettingsLoadReport load_text(const test::TempDir& dir, std::string_view text, Settings& out) {
    test::write_text(dir / "settings.json", text);
    SettingsStore store(dir / "settings.json");
    const SettingsLoadReport report = store.load();
    out = store.settings();
    return report;
}

}  // namespace

TEST_SUITE("settings") {
    TEST_CASE("defaults match the specification") {
        const Settings s;
        CHECK(s.language == "auto");
        CHECK(s.display.mode == WindowMode::Borderless);
        CHECK(s.display.monitor.empty());
        CHECK(s.display.fullscreen_width == 0);
        CHECK(s.display.fullscreen_height == 0);
        CHECK(s.display.vsync);
        CHECK(s.display.fps_limit == 0);
        CHECK(s.display.ui_scale == 0.0);
        CHECK_FALSE(s.display.window_x.has_value());
        CHECK(s.audio.master == 80);
        CHECK(s.audio.music == 70);
    }

    TEST_CASE("a missing file gives defaults and is not created until saving") {
        test::TempDir dir;
        SettingsStore store(dir / "settings.json");
        const auto report = store.load();
        CHECK(report.created_default);
        CHECK(report.ignored_fields == 0);
        CHECK(store.settings() == Settings{});
        CHECK_FALSE(std::filesystem::exists(dir / "settings.json"));
        CHECK(store.save());
        CHECK(std::filesystem::exists(dir / "settings.json"));
    }

    TEST_CASE("round trip keeps every value") {
        test::TempDir dir;
        SettingsStore store(dir / "settings.json");
        (void)store.load();
        Settings& s = store.settings();
        s.language = "es-MX";
        s.display.mode = WindowMode::Fullscreen;
        s.display.monitor = "Pantalla ñ 2";
        s.display.fullscreen_width = 1920;
        s.display.fullscreen_height = 1080;
        s.display.window_width = 1280;
        s.display.window_height = 720;
        s.display.window_x = -1200;
        s.display.window_y = 40;
        s.display.window_maximized = true;
        s.display.vsync = false;
        s.display.fps_limit = 144;
        s.display.ui_scale = 1.25;
        s.audio = AudioSettings{10, 20, 30, 40, 50};
        const Settings expected = s;
        REQUIRE(store.save());

        SettingsStore again(dir / "settings.json");
        const auto report = again.load();
        CHECK(report.ignored_fields == 0);
        CHECK_FALSE(report.read_only);
        CHECK(again.settings() == expected);
    }

    TEST_CASE("the fixture with every field loads without warnings") {
        SettingsStore store(test::fixture("settings/valid_full.json"));
        const auto report = store.load();
        CHECK(report.ignored_fields == 0);
        CHECK(store.settings().display.mode == WindowMode::Windowed);
        CHECK(store.settings().display.window_x == 100);
        CHECK(store.settings().audio.effects == 55);
    }

    TEST_CASE("each invalid field falls back to its default and is counted") {
        test::TempDir dir;
        Settings s;
        SUBCASE("wrong types") {
            const auto r = load_text(dir, R"({"schemaVersion": 1, "language": 5,
                "display": {"mode": 1, "vsync": "yes", "windowWidth": "big"},
                "audio": {"master": true}})", s);
            CHECK(r.ignored_fields == 5);
            CHECK(s == Settings{});
        }
        SUBCASE("out of range") {
            const auto r = load_text(dir, R"({"schemaVersion": 1,
                "display": {"windowWidth": 10, "windowHeight": 100000, "fpsLimit": 10, "uiScale": 5,
                            "fullscreenWidth": 100, "fullscreenHeight": 0},
                "audio": {"master": 101, "music": -1}})", s);
            CHECK(r.ignored_fields == 7);
            CHECK(s == Settings{});
        }
        SUBCASE("bad strings") {
            const auto r = load_text(dir, R"({"schemaVersion": 1, "language": "../../etc",
                "display": {"mode": "cinema", "monitor": "a\u0007b"}})", s);
            CHECK(r.ignored_fields == 3);
            CHECK(s == Settings{});
        }
        SUBCASE("sections of the wrong type") {
            const auto r = load_text(dir, R"({"schemaVersion": 1, "display": [], "audio": 3})", s);
            CHECK(r.ignored_fields == 2);
            CHECK(s == Settings{});
        }
        SUBCASE("half a window position") {
            const auto r = load_text(dir, R"({"schemaVersion": 1, "display": {"windowX": 10}})", s);
            CHECK(r.ignored_fields == 1);
            CHECK_FALSE(s.display.window_x.has_value());
        }
        SUBCASE("missing schema version") {
            const auto r = load_text(dir, R"({"language": "es"})", s);
            CHECK(r.ignored_fields == 1);
            CHECK(s.language == "es");
        }
        SUBCASE("valid fields next to invalid ones are kept") {
            const auto r = load_text(dir, R"({"schemaVersion": 1, "language": "en",
                "audio": {"master": 500, "music": 12}})", s);
            CHECK(r.ignored_fields == 1);
            CHECK(s.language == "en");
            CHECK(s.audio.master == 80);
            CHECK(s.audio.music == 12);
        }
    }

    TEST_CASE("unreadable files are quarantined and defaults are used") {
        test::TempDir dir;
        Settings s;
        std::string content;
        SUBCASE("truncated JSON") { content = R"({"schemaVersion": 1, "display": {"mode": "wind)"; }
        SUBCASE("empty file") { content = ""; }
        SUBCASE("root is not an object") { content = "[1, 2, 3]"; }
        SUBCASE("invalid UTF-8") { content = "{\"language\": \"\xC3\"}"; }
        SUBCASE("larger than the limit") {
            content = R"({"schemaVersion": 1, "pad": ")" +
                      std::string(settings_limits::kMaxFileBytes, 'x') + "\"}";
        }
        const auto r = load_text(dir, content, s);
        CHECK(r.quarantined);
        CHECK(s == Settings{});
        CHECK_FALSE(std::filesystem::exists(dir / "settings.json"));
        REQUIRE(std::filesystem::exists(r.quarantine_path));
        CHECK(test::read_text(r.quarantine_path) == content);
    }

    TEST_CASE("a file from a newer version is read-only and never overwritten") {
        test::TempDir dir;
        const std::string content = R"({"schemaVersion": 99, "language": "es", "futureThing": [1, 2]})";
        test::write_text(dir / "settings.json", content);
        SettingsStore store(dir / "settings.json");
        const auto r = store.load();
        CHECK(r.read_only);
        CHECK(store.settings().language == "es");
        store.settings().language = "en";
        CHECK_FALSE(store.save());
        CHECK(test::read_text(dir / "settings.json") == content);
    }

    TEST_CASE("unknown fields survive a save") {
        test::TempDir dir;
        test::write_text(dir / "settings.json", R"({"schemaVersion": 1, "futureRoot": {"a": [1, "two"]},
            "display": {"mode": "windowed", "futureDisplay": 7}})");
        SettingsStore store(dir / "settings.json");
        CHECK(store.load().ignored_fields == 0);
        store.settings().display.mode = WindowMode::Borderless;
        REQUIRE(store.save());

        const auto parsed = json::parse_object(test::read_text(dir / "settings.json"));
        REQUIRE(parsed.error == json::ParseError::None);
        yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
        yyjson_mut_val* future = nullptr;
        CHECK(json::get_object(root, "futureRoot", future) == json::Field::Ok);
        yyjson_mut_val* display = nullptr;
        REQUIRE(json::get_object(root, "display", display) == json::Field::Ok);
        std::int64_t v = 0;
        CHECK(json::get_int(display, "futureDisplay", 0, 10, v) == json::Field::Ok);
        CHECK(v == 7);
        std::string mode;
        CHECK(json::get_string(display, "mode", 16, mode) == json::Field::Ok);
        CHECK(mode == "borderless");
    }

    TEST_CASE("clearing the window position removes it from the file") {
        test::TempDir dir;
        test::write_text(dir / "settings.json",
                         R"({"schemaVersion": 1, "display": {"windowX": 5, "windowY": 6}})");
        SettingsStore store(dir / "settings.json");
        (void)store.load();
        CHECK(store.settings().display.window_x == 5);
        store.settings().display.window_x.reset();
        store.settings().display.window_y.reset();
        REQUIRE(store.save());
        SettingsStore again(dir / "settings.json");
        (void)again.load();
        CHECK_FALSE(again.settings().display.window_x.has_value());
    }
}

TEST_SUITE("settings") {
    TEST_CASE("graphics, input, interface and gameplay round trip") {
        test::TempDir dir;
        SettingsStore store(dir / "settings.json");
        (void)store.load();
        Settings& s = store.settings();
        s.graphics.apply_preset(QualityPreset::Ultra);
        s.graphics.vegetation = 1;
        s.graphics.preset = s.graphics.matching_preset();
        CHECK(s.graphics.preset == QualityPreset::Custom);
        s.input.bindings.set_key(Action::CameraForward, 0, SDL_SCANCODE_I);
        s.input.bindings.set_key(Action::CameraForward, 1, SDL_SCANCODE_UNKNOWN);
        s.input.camera_pan_speed = 2.5;
        s.input.invert_zoom = true;
        s.ui.font = "some-font";
        s.ui.tooltip_delay_ms = 1200;
        s.gameplay.autosave_minutes = 30;
        s.gameplay.tutorial_seen = true;
        const Settings expected = s;
        REQUIRE(store.save());
        SettingsStore again(dir / "settings.json");
        CHECK(again.load().ignored_fields == 0);
        CHECK(again.settings() == expected);
    }

    TEST_CASE("presets and levels stay consistent") {
        GraphicsSettings g;
        g.apply_preset(QualityPreset::Low);
        CHECK(g.shadows == 0);
        CHECK(g.matching_preset() == QualityPreset::Low);
        g.antialiasing = 3;
        CHECK(g.matching_preset() == QualityPreset::Custom);

        test::TempDir dir;
        Settings s;
        // The stored preset is derived from the levels, never trusted.
        const auto r = load_text(dir, R"({"schemaVersion": 1, "graphics": {"preset": "ultra", "shadows": 0,
            "drawDistance": 0, "vegetation": 0, "antialiasing": 0}})", s);
        CHECK(r.ignored_fields == 0);
        CHECK(s.graphics.preset == QualityPreset::Low);
    }

    TEST_CASE("invalid and duplicate key bindings are rejected") {
        test::TempDir dir;
        Settings s;
        const auto r = load_text(dir, R"({"schemaVersion": 1, "input": {"bindings": {
            "camera.forward": ["NotAKey", ""],
            "camera.back": "S",
            "camera.left": ["A", "B", "C"],
            "game.pause": ["W", ""],
            "unknown.action": ["X"]},
            "cameraZoomSpeed": 9}})", s);
        // forward, back, left invalid; pause takes W from forward's default (duplicate); zoom speed out of range.
        CHECK(r.ignored_fields == 5);
        CHECK(s.input.bindings.matches(Action::CameraForward, SDL_SCANCODE_W));
        CHECK_FALSE(s.input.bindings.matches(Action::GamePause, SDL_SCANCODE_W));
        CHECK(s.input.camera_zoom_speed == 1.0);
    }

    TEST_CASE("interface and gameplay fields are validated") {
        test::TempDir dir;
        Settings s;
        const auto r = load_text(dir, R"({"schemaVersion": 1,
            "ui": {"font": "../evil", "showTooltips": 1, "tooltipDelayMs": 99999},
            "gameplay": {"autosaveMinutes": -5, "autosaveKeep": 0, "tutorialSeen": "no"}})", s);
        CHECK(r.ignored_fields == 6);
        CHECK(s == Settings{});
    }

    TEST_CASE("the game windows' places round-trip and are validated") {
        test::TempDir dir;
        {
            SettingsStore store(dir / "settings.json");
            (void)store.load();
            store.settings().ui.windows = "goods:150,60,440,1,0;stats:150,300,380,0,2;";
            REQUIRE(store.save());
        }
        SettingsStore again(dir / "settings.json");
        CHECK(again.load().ignored_fields == 0);
        CHECK(again.settings().ui.windows == "goods:150,60,440,1,0;stats:150,300,380,0,2;");
        Settings s;
        const auto r = load_text(dir, R"({"schemaVersion": 1, "ui": {"windows": "goods:1,2,3,0,0;\"x\"=rm"}})", s);
        CHECK(r.ignored_fields == 1);
        CHECK(s.ui.windows.empty());
    }

    TEST_CASE("the last new game round-trips") {
        test::TempDir dir;
        NewGameSettings n;
        n.mode = "custom";
        n.size = "colossal";
        n.players = 7;
        n.biomes = {"core:boreal", "core:mountain"};
        n.temperature = 25;
        n.humidity = 175;
        n.climate = "even";
        n.rivers = 200;
        n.lakes = 0;
        n.forests = 50;
        n.resources = 150;
        n.relief = 175;
        n.landforms = 125;
        n.giants_on = false;
        n.giants = 75;
        n.sea = "archipelago";
        n.islands = 5;
        n.seasons = 0b1000;
        n.season_minutes = {1, 30, 12, 7};
        n.day_night = false;
        n.day_minutes = 30;
        n.night_minutes = 1;
        n.winter = "harsh";
        n.start = "plenty";
        n.diseases = "none";
        n.fires = "brutal";
        n.raiders = "low";
        n.wildlife = "high";
        n.race = "mixed";
        n.other_races = 50;
        n.immigrants = {"core:elf"};
        n.max_population = 350;
        n.fog = "dynamic";
        n.shared_vision = false;
        {
            SettingsStore store(dir / "settings.json");
            (void)store.load();
            store.settings().new_game = n;
            REQUIRE(store.save());
        }
        SettingsStore again(dir / "settings.json");
        CHECK(again.load().ignored_fields == 0);
        CHECK(again.settings().new_game == n);
    }

    TEST_CASE("each invalid new game field falls back on its own") {
        test::TempDir dir;
        Settings s;
        const auto r = load_text(dir, R"({"schemaVersion": 1, "newGame": {
            "mode": "random", "size": "enormous", "players": 13, "biomes": ["../x"], "temperature": 225,
            "humidity": -25, "climate": "odd", "rivers": "lots", "lakes": 300, "relief": "cliffs",
            "islands": 9, "sea": "ocean", "seasons": 16, "year": 0, "winter": "cold",
            "startGoods": "none", "diseases": "extreme", "race": "mixed!", "otherRaces": 201,
            "immigrants": "all", "maxPopulation": 20, "fog": "thick", "sharedVision": 1,
            "resources": 150, "fires": "low", "forests": 50, "giantsOn": false}})", s);
        CHECK(r.ignored_fields == 23);
        NewGameSettings expected;
        expected.resources = 150;
        expected.fires = "low";
        expected.forests = 50;
        expected.giants_on = false;
        CHECK(s.new_game == expected);
        // A percent off its steps of 25 is not taken.
        Settings t;
        (void)load_text(dir, R"({"schemaVersion": 1, "newGame": {"rivers": 60, "lakes": 125}})", t);
        CHECK(t.new_game.rivers == 100);
        CHECK(t.new_game.lakes == 125);
    }

    TEST_CASE("the form of before phase 56 is accepted and opens as a varied map") {
        test::TempDir dir;
        Settings s;
        const auto r = load_text(dir, R"({"schemaVersion": 1, "newGame": {
            "size": "large", "mapType": "core:islands", "biome": "core:temperate", "islands": 3, "sea": "always",
            "water": "normal", "forests": "high", "resources": "normal", "relief": "gentle", "landforms": "low",
            "players": 2, "seasons": 15, "year": "normal", "winter": "mild", "startGoods": "normal",
            "diseases": "medium", "fires": "medium", "raiders": "high", "wildlife": "medium", "race": "core:elf",
            "otherRaces": 20, "maxPopulation": 600, "fog": "static", "sharedVision": true}})", s);
        // What still means the same is kept; the rest is the usual.
        CHECK(s.new_game.mode == "varied");
        CHECK(s.new_game.size == "large");
        CHECK(s.new_game.players == 2);
        CHECK(s.new_game.islands == 3);
        CHECK(s.new_game.winter == "mild");
        CHECK(s.new_game.raiders == "high");
        CHECK(s.new_game.race == "core:elf");
        CHECK(s.new_game.max_population == 600);
        CHECK(s.new_game.forests == 100);
        CHECK(s.new_game.sea == "none");
        CHECK(s.new_game.season_minutes == std::array<int, 4>{5, 5, 5, 5});
        CHECK(r.ignored_fields > 0);
        CHECK(is_valid_def_id("core:giants"));
        CHECK_FALSE(is_valid_def_id(""));
        CHECK_FALSE(is_valid_def_id("core/../x"));
        CHECK_FALSE(is_valid_def_id(std::string(65, 'a')));
    }
}
