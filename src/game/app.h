// Application: owns the window, the GPU device, the settings and the main
// loop.
#pragma once

#include <cstdint>
#include <optional>

#include <SDL3/SDL_events.h>

#include "game/game_clock.h"
#include "game/settings.h"
#include "platform/paths.h"
#include "platform/window.h"
#include "render/gpu_device.h"

namespace sc {

class App {
public:
    App() = default;
    App(const App&) = delete;
    App& operator=(const App&) = delete;

    int run();

private:
    bool init();
    void shutdown();
    void handle_event(const SDL_Event& event);
    void frame();
    void set_window_mode(WindowMode mode);
    void mark_settings_dirty();
    void save_settings_if_due(bool force);

    std::optional<DataPaths> paths_;
    std::optional<SettingsStore> settings_;
    Window window_;
    GpuDevice gpu_;
    GameClock clock_;
    bool running_ = true;
    bool sdl_ready_ = false;
    std::uint64_t last_frame_ns_ = 0;
    std::uint64_t settings_dirty_since_ns_ = 0;  // 0 = nothing to save.
    WindowMode last_fullscreen_mode_ = WindowMode::Borderless;
};

}  // namespace sc
