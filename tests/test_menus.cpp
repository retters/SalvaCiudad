#include <doctest.h>

#include <array>

#include "core/file_io.h"
#include "sim/worldgen.h"
#include "game/menu_backgrounds.h"
#include "game/settings_screen.h"
#include "game/services.h"
#include "game/ui_host.h"
#include "i18n/translator.h"
#include "test_util.h"
#include "ui/context.h"
#include "ui/font.h"
#include "ui/text.h"

using namespace sc;

namespace {

// Records what the menus ask of the application.
class FakeServices final : public Services {
public:
    Settings settings_value;
    std::vector<DisplaySettings> applied;
    bool refuse = false;
    int saves_requested = 0;
    ui::FontLibrary font_library;

    Settings& settings() override { return settings_value; }
    void settings_changed() override { ++saves_requested; }
    bool apply_display(const DisplaySettings& d) override {
        applied.push_back(d);
        return !refuse;
    }
    void apply_vsync() override {}
    void apply_graphics() override {}
    bool scene_available() const override { return false; }
    CameraMode camera_mode() const override { return CameraMode::Aerial; }
    void apply_language() override {}
    void apply_font() override {}
    std::vector<std::string> monitor_names() override { return {"Monitor A"}; }
    std::vector<Resolution> fullscreen_resolutions(const std::string&) override { return {{1920, 1080}}; }
    const ui::FontLibrary& fonts() const override { return font_library; }
    rml::RmlUi* rml() override { return nullptr; }
    void set_hud_image(const std::string&, int, int, const std::vector<std::uint8_t>&) override {}
    std::vector<UiStyleChoice> ui_styles() const override {
        return {{"frosted", "Frosted", {0xeef0f4ffu, 0x1b1f24ffu, 0x5b5bd6ffu, 0x18794effu, 0xad5700ffu, 0xcd2b31ffu}},
                {"vidrio", "Vidrio oscuro", {0x15142affu, 0xf1f0ffffu, 0x9b7bffffu, 0x49f2b0ffu, 0xffd166ffu, 0xff5c8affu}}};
    }
    void open_data_folder() override {}
    void request_quit() override {}
    mods::ModLibrary& mod_library() override { return library; }
    void apply_mods(const std::vector<std::string>& enabled) override { applied_mods = enabled; }
    void open_mods_folder() override {}
    const sim::Content* content() const override { return &sc::test::core_content(); }
    mods::ModLibrary library;
    std::vector<std::string> applied_mods;
    void start_map_generation(const sim::MapSettings& settings, const sim::GameRules&, bool) override {
        generation_started = true;
        last_map_settings = settings;
    }
    MapGenStatus map_generation_status() const override { return generation_status; }
    void cancel_map_generation() override { generation_status.state = MapGenStatus::State::Cancelled; }
    bool enter_generated_map() override { return false; }
    void leave_map() override {}
    const sim::MapData* current_map() const override { return game ? &game->game().map() : nullptr; }

    GameSession* session() override { return game.get(); }
    int game_speed() const override { return speed; }
    void set_game_speed(int s) override { speed = s; }
    int max_game_speed() const override { return 36; }
    void save_game() override { ++games_saved; }
    std::vector<save::Entry> list_saves() override { return saves; }
    bool load_game(const std::filesystem::path& file) override {
        loaded.push_back(file);
        return false;
    }

    bool host_game(const sim::MapSettings&, const sim::GameRules&) override { return false; }
    bool join_game(const std::string&, std::uint16_t) override { return false; }
    void leave_network() override {}
    bool open_game(std::uint8_t access) override {
        opened_access = access;
        return true;
    }
    void set_access(std::uint8_t access) override { opened_access = access; }
    [[nodiscard]] bool hosting() const override { return false; }
    bool load_game_as_host(const std::filesystem::path& file) override {
        hosted = file;
        return true;
    }
    [[nodiscard]] int saved_access() const override { return -1; }
    void watch_game() override {}
    void play_game(int) override {}
    std::filesystem::path hosted;
    int opened_access = -1;
    net::NetSession* net() override { return nullptr; }
    void set_lan_search(bool) override {}
    std::vector<net::LanGame> lan_games() override { return {}; }
    std::string player_name() const override { return "Tester"; }
    void focus_camera(float x, float z) override {
        focused_x = x;
        focused_z = z;
    }
    int overlay() const override { return layer; }
    std::array<float, 3> camera_view() const override { return {0.0f, 0.0f, 60.0f}; }
    const std::vector<mods::ModScript>* mod_scripts() const override { return nullptr; }
    void set_overlay(int l) override { layer = l; }
    CameraGround camera_ground() const override { return ground; }
    void set_ui_image(std::uint32_t id, int width, int height, std::vector<std::uint8_t> rgba) override {
        image_id = id;
        image_width = width;
        image_height = height;
        image_bytes = rgba.size();
    }
    CameraGround ground;
    std::uint32_t image_id = 0;
    int image_width = 0;
    int image_height = 0;
    std::size_t image_bytes = 0;
    float focused_x = -1.0f;
    float focused_z = -1.0f;
    int layer = 0;

    bool generation_started = false;
    sim::MapSettings last_map_settings;
    MapGenStatus generation_status;
    std::unique_ptr<GameSession> game;
    int speed = 4;
    int games_saved = 0;
    std::vector<save::Entry> saves;
    std::vector<std::filesystem::path> loaded;
};

struct Harness {
    std::unique_ptr<ui::Font> font = std::make_unique<ui::Font>();
    ui::GlyphAtlas atlas{512};
    ui::TextRenderer text{atlas};
    ui::Context ctx{text};
    FakeServices services;
    UiHost host{services};

    Harness() {
        const auto r = fs::read_file(std::filesystem::path(SC_SOURCE_DIR) / "data/fonts/ui/AlegreyaSans-Regular.ttf",
                                     ui::Font::kMaxFileBytes);
        REQUIRE(font->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end())));
        text.set_font(ui::FontRole::Regular, font.get());
        services.settings_value.display.mode = WindowMode::Windowed;
    }

    void frame(std::uint64_t ms, const ui::Input& input = {}) {
        ctx.begin_frame(input, 1280, 720, 1.0f, ms * 1'000'000ull, 0, 0);
        host.frame(ctx);
        ctx.end_frame();
    }
};

}  // namespace

TEST_SUITE("menus") {
    TEST_CASE("the main menu logo is picked at random, never the same twice in a row") {
        CHECK(pick_logo_style(-1, 1, 12345) == 0);
        CHECK(pick_logo_style(0, 1, 12345) == 0);
        std::array<int, 6> first{};
        for (std::uint64_t r = 0; r < 600; ++r) {
            const int s = pick_logo_style(-1, 6, r * 0x9E3779B97F4A7C15ull);
            REQUIRE(s >= 0);
            REQUIRE(s < 6);
            ++first[static_cast<std::size_t>(s)];
        }
        for (const int n : first) {
            CHECK(n > 50);  // Every style comes up.
        }
        for (int current = 0; current < 6; ++current) {
            std::array<int, 6> next{};
            for (std::uint64_t r = 0; r < 500; ++r) {
                ++next[static_cast<std::size_t>(pick_logo_style(current, 6, r))];
            }
            for (int s = 0; s < 6; ++s) {
                CHECK(next[static_cast<std::size_t>(s)] == (s == current ? 0 : 100));
            }
        }
    }

    TEST_CASE("a risky display change reverts by itself after 15 seconds") {
        Harness h;
        DisplaySettings wanted = h.services.settings_value.display;
        wanted.mode = WindowMode::Borderless;
        h.host.change_display(wanted);
        REQUIRE(h.services.applied.size() == 1);
        CHECK(h.services.settings_value.display.mode == WindowMode::Borderless);

        h.frame(1000);   // Countdown starts on the first frame.
        h.frame(15000);  // 14 s later: still waiting.
        CHECK(h.services.applied.size() == 1);
        h.frame(16001);
        REQUIRE(h.services.applied.size() == 2);
        CHECK(h.services.applied.back().mode == WindowMode::Windowed);
        CHECK(h.services.settings_value.display.mode == WindowMode::Windowed);
    }

    TEST_CASE("Esc in the dialog reverts at once") {
        Harness h;
        DisplaySettings wanted = h.services.settings_value.display;
        wanted.mode = WindowMode::Fullscreen;
        h.host.change_display(wanted);
        h.frame(0);
        ui::Input esc;
        esc.keys.push_back(SDL_SCANCODE_ESCAPE);
        h.frame(100, esc);
        REQUIRE(h.services.applied.size() == 2);
        CHECK(h.services.settings_value.display.mode == WindowMode::Windowed);
    }

    TEST_CASE("changing again during the countdown still reverts to the original") {
        Harness h;
        DisplaySettings a = h.services.settings_value.display;
        a.mode = WindowMode::Borderless;
        h.host.change_display(a);
        h.frame(0);
        DisplaySettings b = a;
        b.mode = WindowMode::Fullscreen;
        h.host.change_display(b);
        h.frame(100);
        h.frame(20000);
        CHECK(h.services.settings_value.display.mode == WindowMode::Windowed);
    }

    TEST_CASE("a refused change keeps the settings and shows a message") {
        Harness h;
        h.services.refuse = true;
        DisplaySettings wanted = h.services.settings_value.display;
        wanted.mode = WindowMode::Fullscreen;
        h.host.change_display(wanted);
        CHECK(h.services.settings_value.display.mode == WindowMode::Windowed);
        h.frame(0);
        h.frame(30000);
        CHECK(h.services.applied.size() == 1);  // No revert needed.
    }

    TEST_CASE("vsync and frame limit changes need no confirmation") {
        Harness h;
        DisplaySettings wanted = h.services.settings_value.display;
        wanted.vsync = false;
        h.host.change_display(wanted);
        h.frame(0);
        h.frame(20000);
        CHECK(h.services.applied.size() == 1);
        CHECK_FALSE(h.services.settings_value.display.vsync);
    }

    // Phase 126: the menus are RmlUi panels of rows; their buttons do what
    // the old ones did.
    TEST_CASE("the main menu's buttons open their screens") {
        Harness h;
        h.frame(0);
        const ThingRows* main = h.host.menu_rows("main");
        REQUIRE(main != nullptr);
        const auto press = [&](const ThingRows& rows, const std::string& label) {
            for (const WinRow& r : rows.rows) {
                for (const RowButton& b : r.buttons) {
                    if (b.label == label) {
                        REQUIRE(b.enabled);
                        RowEffects e;
                        rows.acts[static_cast<std::size_t>(b.act)](nullptr, RowInput{}, e);
                        return;
                    }
                }
            }
            FAIL("no button " << label);
        };
        press(*main, i18n::tr("menu.main.settings"));
        h.frame(16);
        CHECK(h.host.menu_rows("main") == nullptr);
        REQUIRE(h.host.menu_rows("settings") != nullptr);
        // Esc goes back.
        ui::Input esc;
        esc.keys.push_back(SDL_SCANCODE_ESCAPE);
        h.frame(32, esc);
        h.frame(48);
        REQUIRE(h.host.menu_rows("main") != nullptr);
        press(*h.host.menu_rows("main"), i18n::tr("menu.main.singlePlayer"));
        h.frame(64);
        REQUIRE(h.host.menu_rows("new_game") != nullptr);
        press(*h.host.menu_rows("new_game"), i18n::tr("newGame.generate"));
        h.frame(80);
        CHECK(h.services.generation_started);
    }

    TEST_CASE("every setting is saved when changed, and each tab restores its defaults") {
        Harness h;
        SettingsScreen screen(h.services);
        const Settings defaults;
        for (int t = 0; t < static_cast<int>(SettingsScreen::Tab::Count); ++t) {
            const auto tab = static_cast<SettingsScreen::Tab>(t);
            if (tab == SettingsScreen::Tab::Display) {
                continue;  // Its changes go through the countdown (the tests above).
            }
            screen.show_tab(tab);
            // Each choice with arrows, a step on: the change is saved.
            const std::size_t rows = screen.rows(h.host).rows.size();
            for (std::size_t i = 0; i < rows; ++i) {
                const ThingRows view = screen.rows(h.host);
                REQUIRE(view.rows.size() == rows);
                const WinRow& row = view.rows[i];
                const RowButton* step = nullptr;
                // A choice (its value between the arrows) or a check box.
                const bool setting = !row.detail.empty() ||
                                     (!row.buttons.empty() && (row.buttons.back().icon == "icon-check" || row.buttons.back().icon == "icon-minus"));
                if (row.kind == WinRow::Kind::Stepper && setting && row.buttons.back().enabled) {
                    step = &row.buttons.back();
                }
                RowEffects e;
                const int saved = h.services.saves_requested;
                const Settings before = h.services.settings_value;
                if (step != nullptr) {
                    view.acts[static_cast<std::size_t>(step->act)](nullptr, RowInput{}, e);
                } else if (row.kind == WinRow::Kind::Slider && row.enabled) {
                    const int to = row.value + row.step <= row.max ? row.value + row.step : row.value - row.step;
                    view.acts[static_cast<std::size_t>(row.act)](nullptr, RowInput{to, {}, false}, e);
                } else {
                    continue;
                }
                CHECK_MESSAGE(h.services.saves_requested > saved, "tab " << t << ", row " << i << ": " << row.text);
                CHECK_MESSAGE(!(h.services.settings_value == before), "tab " << t << ", row " << i << ": " << row.text);
            }
            // "Restore defaults" brings the tab back.
            const ThingRows view = screen.rows(h.host);
            const RowButton& restore = view.rows.back().buttons.front();
            RowEffects e;
            view.acts[static_cast<std::size_t>(restore.act)](nullptr, RowInput{}, e);
            const Settings& s = h.services.settings_value;
            switch (tab) {
                case SettingsScreen::Tab::Graphics: CHECK(s.graphics == defaults.graphics); break;
                case SettingsScreen::Tab::Audio: CHECK(s.audio == defaults.audio); break;
                case SettingsScreen::Tab::Controls: CHECK(s.input == defaults.input); break;
                case SettingsScreen::Tab::Interface: CHECK(s.ui == defaults.ui); break;
                case SettingsScreen::Tab::Language: CHECK(s.language == defaults.language); break;
                case SettingsScreen::Tab::Game: CHECK(s.gameplay == defaults.gameplay); break;
                default: break;
            }
        }
        // A key binding: the next key pressed.
        screen.show_tab(SettingsScreen::Tab::Controls);
        const ThingRows view = screen.rows(h.host);
        const auto key_row = std::find_if(view.rows.begin(), view.rows.end(),
                                          [](const WinRow& r) { return r.cls.find("keys") != std::string::npos; });
        REQUIRE(key_row != view.rows.end());
        RowEffects e;
        view.acts[static_cast<std::size_t>(key_row->buttons.front().act)](nullptr, RowInput{}, e);
        CHECK(screen.capturing_key());
        screen.key_pressed(SDL_SCANCODE_F8);
        CHECK_FALSE(screen.capturing_key());
        Action action{};
        std::size_t slot = 0;
        CHECK(h.services.settings_value.input.bindings.find(SDL_SCANCODE_F8, action, slot));
    }

    TEST_CASE("the game interface places buildings, pauses and saves") {
        Harness h;
        sim::MapSettings ms;
        ms.seed = 3;
        ms.size = sim::MapSize::Small;
        std::optional<sim::MapData> map = sim::generate_map(ms, sc::test::core_content());
        REQUIRE(map.has_value());
        const std::shared_ptr<const sim::Content> content(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
        sim::GameSetup setup;
        setup.seed = 1;
        h.services.game = std::make_unique<GameSession>(content, std::move(*map), setup);
        GameSession::Interaction& ui = h.services.game->ui();
        h.host.show_game();
        h.frame(0);
        // Phases 121 and 122: the top bar, the minimap and the build bar are
        // RmlUi's (no RmlUi here); a building is picked as its button does.
        CHECK_FALSE(h.host.game_paused());
        const sim::DefIndex house = h.services.game->game().content().find_building("core:house");
        REQUIRE(house != sim::kNoDef);
        ui.placing = house;
        h.frame(16);
        REQUIRE(ui.placing != sim::kNoDef);

        ui::Input key;
        key.keys.push_back(SDL_SCANCODE_R);
        h.frame(48, key);
        CHECK(ui.rotation == 1);

        // Esc cancels the placing first, then opens the menu, which pauses.
        key.keys = {SDL_SCANCODE_ESCAPE};
        h.frame(64, key);
        CHECK(ui.placing == sim::kNoDef);
        CHECK_FALSE(h.host.game_paused());
        h.frame(80, key);
        CHECK(h.host.game_paused());
        h.frame(96, key);  // Esc again closes it.
        CHECK_FALSE(h.host.game_paused());

        // Space pauses and resumes; the number keys set the speed.
        key.keys = {SDL_SCANCODE_SPACE};
        h.frame(112, key);
        CHECK(h.services.speed == 0);
        CHECK(h.host.game_paused());
        // A pause is only speed 0: no veil, and the interface still works.
        CHECK_FALSE(h.host.scene_paused());
        ui.placing = house;
        h.frame(116);
        CHECK(ui.placing != sim::kNoDef);
        ui::Input esc;
        esc.keys = {SDL_SCANCODE_ESCAPE};
        h.frame(118, esc);
        CHECK(ui.placing == sim::kNoDef);
        CHECK(h.services.speed == 0);
        h.frame(128, key);
        CHECK(h.services.speed == 4);
        key.keys = {SDL_SCANCODE_3};
        h.frame(144, key);
        CHECK(h.services.speed == 12);  // x3, in quarters.
        // Period and comma go a step up and down the table.
        key.keys = {SDL_SCANCODE_PERIOD};
        h.frame(146, key);
        CHECK(h.services.speed == 16);
        key.keys = {SDL_SCANCODE_COMMA};
        h.frame(148, key);
        h.frame(150, key);
        CHECK(h.services.speed == 8);

        key.keys = {SDL_SCANCODE_F5};
        h.frame(160, key);
        CHECK(h.services.games_saved == 1);
    }

    TEST_CASE("the menu background's seed list is read strictly and written back") {
        namespace mb = sc::menu_backgrounds;
        std::vector<std::uint64_t> seeds;
        std::string error;
        REQUIRE(mb::parse(R"({"schemaVersion": 1, "seeds": ["7", "18446744073709551615", "7"]})", seeds, error));
        CHECK(seeds == std::vector<std::uint64_t>{7, 18446744073709551615ull});  // Repeats are dropped.
        std::vector<std::uint64_t> back;
        REQUIRE(mb::parse(mb::to_json(seeds), back, error));
        CHECK(back == seeds);
        for (const char* bad : {"", "[]", R"({"seeds": ["1"]})", R"({"schemaVersion": 2, "seeds": ["1"]})",
                                R"({"schemaVersion": 1})", R"({"schemaVersion": 1, "seeds": "1"})",
                                R"({"schemaVersion": 1, "seeds": [1]})", R"({"schemaVersion": 1, "seeds": ["-1"]})",
                                R"({"schemaVersion": 1, "seeds": ["1x"]})", R"({"schemaVersion": 1, "seeds": [""]})",
                                R"({"schemaVersion": 1, "seeds": ["18446744073709551616"]})"}) {
            std::vector<std::uint64_t> out{99};
            CHECK_FALSE_MESSAGE(mb::parse(bad, out, error), bad);
            CHECK(out == std::vector<std::uint64_t>{99});  // Left alone.
        }
        std::string many = R"({"schemaVersion": 1, "seeds": [)";
        for (std::size_t i = 0; i <= mb::kMaxSeeds; ++i) {
            many += (i ? ",\"" : "\"") + std::to_string(i) + "\"";
        }
        CHECK_FALSE(mb::parse(many + "]}", seeds, error));

        // The list that ships is valid and not empty.
        const std::vector<std::uint64_t> shipped =
            mb::load(std::filesystem::path(SC_SOURCE_DIR) / "data" / mb::kFileName);
        CHECK_FALSE(shipped.empty());

        // Choosing wraps over the two lists; with none there is still a seed.
        CHECK(mb::choose({}, {}, 5) == mb::kFallbackSeed);
        CHECK(mb::choose({10, 20}, {30}, 0) == 10);
        CHECK(mb::choose({10, 20}, {30}, 2) == 30);
        CHECK(mb::choose({10, 20}, {30}, 4) == 20);

        // Saving a seed: in a new file, once, and next to the others.
        const test::TempDir dir;
        const std::filesystem::path file = dir / "menu_backgrounds.json";
        CHECK(mb::load(file).empty());
        REQUIRE(mb::add(file, 42));
        REQUIRE(mb::add(file, 43));
        REQUIRE(mb::add(file, 42));
        CHECK(mb::load(file) == std::vector<std::uint64_t>{42, 43});
        test::write_text(file, "not json");
        CHECK(mb::load(file).empty());

        // The map: small, with one start (the generator needs one).
        const sim::MapSettings ms = mb::settings_for(42);
        CHECK(ms.seed == 42);
        CHECK(ms.size == sim::MapSize::Small);
    }
}
