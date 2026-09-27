#include <doctest.h>

#include "core/file_io.h"
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
    void start_map_generation(const sim::MapSettings& settings) override {
        generation_started = true;
        last_map_settings = settings;
    }
    MapGenStatus map_generation_status() const override { return generation_status; }
    void cancel_map_generation() override { generation_status.state = MapGenStatus::State::Cancelled; }
    bool enter_generated_map() override { return false; }
    void leave_map() override {}
    const sim::MapData* current_map() const override { return nullptr; }

    bool generation_started = false;
    sim::MapSettings last_map_settings;
    MapGenStatus generation_status;
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
}
