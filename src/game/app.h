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
#include "game/map_generation.h"
#include "game/map_scene.h"
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
#include "sim/simulation.h"
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
    CameraMode camera_mode() const override { return camera_.mode(); }
    void apply_language() override;
    void apply_font() override;
    std::vector<std::string> monitor_names() override;
    std::vector<Resolution> fullscreen_resolutions(const std::string& monitor) override;
    const ui::FontLibrary& fonts() const override { return fonts_; }
    void open_data_folder() override;
    void request_quit() override { running_ = false; }
    void start_map_generation(const sim::MapSettings& settings) override;
    MapGenStatus map_generation_status() const override { return map_job_.status(); }
    void cancel_map_generation() override { map_job_.cancel(); }
    bool enter_generated_map() override;
    void leave_map() override;
    const sim::MapData* current_map() const override { return map_ ? &map_->map : nullptr; }

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
    void handle_scene_click(std::uint32_t width, std::uint32_t height);
    void draw_scene_markers(std::uint32_t width, std::uint32_t height);
    void draw_start_markers(std::uint32_t width, std::uint32_t height);
    void reset_camera_to_test_scene();
    // True in the views the player moves the camera in.
    [[nodiscard]] bool interactive_scene() const;
    void update_mouse_capture();
    [[nodiscard]] math::Mat4 camera_view_proj(std::uint32_t width, std::uint32_t height) const;
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
    MapScene map_scene_;
    MapGenerationJob map_job_;
    std::unique_ptr<GeneratedMap> map_;  // The map being shown.
    bool scene_ok_ = false;
    Camera camera_;
    DebugOverlay debug_;
    DebugInfo debug_info_;
    float camera_wheel_ = 0.0f;   // Wheel notches since the last camera update.
    float camera_drag_px_ = 0.0f;  // Middle-button drag since the last update.
    bool middle_down_ = false;
    bool right_down_ = false;
    float camera_drag_py_ = 0.0f;  // Vertical drag (third person pitch).
    float camera_look_dx_ = 0.0f;  // Relative mouse motion (first person).
    float camera_look_dy_ = 0.0f;
    float press_x_ = 0.0f;         // Where the left button went down.
    float press_y_ = 0.0f;
    bool mouse_captured_ = false;
    std::optional<std::size_t> selected_;  // Villager in the test crowd.
    bool following_ = false;
    bool stress_view_active_ = false;
    float fps_window_s_ = 0.0f;
    int fps_window_frames_ = 0;
    float perf_log_s_ = 0.0f;
    int perf_log_frames_ = 0;
    GameClock clock_;
    // The deterministic simulation, stepped by the clock on the main thread
    // (decision D-506). For now it runs the phase 5 test world.
    sim::Simulation sim_{0};
    bool running_ = true;
    bool sdl_ready_ = false;
    std::uint64_t last_frame_ns_ = 0;
    std::uint64_t settings_dirty_since_ns_ = 0;  // 0 = nothing to save.
    WindowMode last_fullscreen_mode_ = WindowMode::Borderless;
};

}  // namespace sc
