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
