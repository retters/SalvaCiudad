#include <doctest.h>

#include "core/file_io.h"
#include "sim/worldgen.h"
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
    void open_data_folder() override {}
    void request_quit() override {}
    mods::ModLibrary& mod_library() override { return library; }
    void apply_mods(const std::vector<std::string>& enabled) override { applied_mods = enabled; }
    void open_mods_folder() override {}
    const sim::Content* content() const override { return &sc::test::core_content(); }
    mods::ModLibrary library;
    std::vector<std::string> applied_mods;
    void start_map_generation(const sim::MapSettings& settings, const sim::GameRules&) override {
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
    void save_game() override { ++games_saved; }
    std::vector<save::Entry> list_saves() override { return saves; }
    bool load_game(const std::filesystem::path& file) override {
        loaded.push_back(file);
        return false;
    }

    bool host_game(const sim::MapSettings&, const sim::GameRules&) override { return false; }
    bool join_game(const std::string&, std::uint16_t) override { return false; }
    void leave_network() override {}
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
    int speed = 1;
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
        REQUIRE(ui.hud_rects.size() >= 2);
        CHECK_FALSE(h.host.game_paused());
        // Phase 24: the minimap's picture, and a click on it moves the camera.
        CHECK(h.services.image_id == 1u);
        CHECK(h.services.image_width == 256);
        CHECK(h.services.image_bytes == 256u * 256u * 4u);
        {
            // At 1280 x 720: 200 wide, 28 from the right, 72 from the top.
            ui::Input click;
            click.mouse_x = 1280.0f - 28.0f - 150.0f;
            click.mouse_y = 72.0f + 150.0f;
            click.mouse_down = true;
            click.mouse_pressed = true;
            h.frame(8, click);
            const float map_side = static_cast<float>(h.services.game->game().map().size);
            CHECK(h.services.focused_x == doctest::Approx(map_side * 0.25f).epsilon(0.02));
            CHECK(h.services.focused_z == doctest::Approx(map_side * 0.75f).epsilon(0.02));
            CHECK(ui.over_hud(click.mouse_x, click.mouse_y));
            ui::Input up;
            up.mouse_released = true;
            h.frame(12, up);
        }

        // The first button of the build bar starts placing a building.
        const auto bar = ui.hud_rects[1];
        ui::Input press;
        press.mouse_x = bar[0] + 8.0f + 75.0f;
        press.mouse_y = bar[1] + 8.0f + 32.0f + 6.0f + 22.0f;  // Below the category tabs.
        press.mouse_down = true;
        press.mouse_pressed = true;
        h.frame(16, press);
        ui::Input release = press;
        release.mouse_down = false;
        release.mouse_pressed = false;
        release.mouse_released = true;
        h.frame(32, release);
        REQUIRE(ui.placing != sim::kNoDef);
        CHECK(ui.over_hud(press.mouse_x, press.mouse_y));

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
        h.frame(114, press);
        h.frame(116, release);
        CHECK(ui.placing != sim::kNoDef);
        ui::Input esc;
        esc.keys = {SDL_SCANCODE_ESCAPE};
        h.frame(118, esc);
        CHECK(ui.placing == sim::kNoDef);
        CHECK(h.services.speed == 0);
        h.frame(128, key);
        CHECK(h.services.speed == 1);
        key.keys = {SDL_SCANCODE_3};
        h.frame(144, key);
        CHECK(h.services.speed == 3);

        key.keys = {SDL_SCANCODE_F5};
        h.frame(160, key);
        CHECK(h.services.games_saved == 1);
    }
}
