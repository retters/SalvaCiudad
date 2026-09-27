// Application: owns the window, the GPU, the settings, the interface and the
// main loop, and provides the services the menus use.
#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <SDL3/SDL_events.h>

#include "game/camera.h"
#include "game/game_clock.h"
#include "game/services.h"
#include "game/settings.h"
#include "game/test_scene.h"
#include "game/ui_host.h"
#include "platform/paths.h"
#include "platform/window.h"
#include "render/debug_overlay.h"
#include "render/gpu_device.h"
#include "render/scene_renderer.h"
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
    void apply_graphics() override;
    bool scene_available() const override { return scene_ok_; }
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
    void render_frame(float dt);
    void update_camera(float dt);
    void update_frame_stats(float dt);
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
    render::SceneRenderer scene_;
    render::Lighting lighting_;
    TestScene test_scene_;
    TestCrowd crowd_;
    bool scene_ok_ = false;
    Camera camera_;
    DebugOverlay debug_;
    DebugInfo debug_info_;
    float camera_wheel_ = 0.0f;   // Wheel notches since the last camera update.
    float camera_drag_px_ = 0.0f;  // Middle-button drag since the last update.
    bool middle_down_ = false;
    bool stress_view_active_ = false;
    float fps_window_s_ = 0.0f;
    int fps_window_frames_ = 0;
    float perf_log_s_ = 0.0f;
    int perf_log_frames_ = 0;
    GameClock clock_;
    bool running_ = true;
    bool sdl_ready_ = false;
    std::uint64_t last_frame_ns_ = 0;
    std::uint64_t settings_dirty_since_ns_ = 0;  // 0 = nothing to save.
    WindowMode last_fullscreen_mode_ = WindowMode::Borderless;
};

}  // namespace sc
