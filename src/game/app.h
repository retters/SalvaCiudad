// Application: owns the window, the GPU, the settings, the interface and the
// main loop, and provides the services the menus use.
#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <SDL3/SDL_events.h>

#include "game/game_clock.h"
#include "game/services.h"
#include "game/settings.h"
#include "game/ui_host.h"
#include "platform/paths.h"
#include "platform/window.h"
#include "render/gpu_device.h"
#include "render/ui_renderer.h"
#include "ui/context.h"
#include "ui/font_library.h"
#include "ui/glyph_atlas.h"
#include "ui/text.h"

namespace sc {

class App final : public Services {
public:
    App();
    ~App() override;
    App(const App&) = delete;
    App& operator=(const App&) = delete;

    int run();

    // Services.
    Settings& settings() override { return settings_->settings(); }
    void settings_changed() override;
    bool apply_display(const DisplaySettings& display) override;
    void apply_vsync() override;
    void apply_language() override;
    void apply_font() override;
    std::vector<std::string> monitor_names() override;
    std::vector<Resolution> fullscreen_resolutions(const std::string& monitor) override;
    const ui::FontLibrary& fonts() const override { return fonts_; }
    void open_data_folder() override;
    void request_quit() override { running_ = false; }

private:
    bool init();
    void shutdown();
    void load_languages();
    void fatal_error(const char* text_key);
    void handle_event(const SDL_Event& event);
    void frame();
    void render_ui();
    void cycle_window_mode();
    void save_settings_if_due(bool force);
    [[nodiscard]] float ui_scale() const;

    std::optional<DataPaths> paths_;
    std::optional<SettingsStore> settings_;
    Window window_;
    GpuDevice gpu_;
    UiRenderer ui_renderer_;
    ui::FontLibrary fonts_;
    ui::GlyphAtlas atlas_;
    ui::TextRenderer text_;
    ui::Context ui_;
    std::unique_ptr<UiHost> host_;
    ui::Input input_;
    GameClock clock_;
    bool running_ = true;
    bool sdl_ready_ = false;
    std::uint64_t last_frame_ns_ = 0;
    std::uint64_t settings_dirty_since_ns_ = 0;  // 0 = nothing to save.
    WindowMode last_fullscreen_mode_ = WindowMode::Borderless;
};

}  // namespace sc
