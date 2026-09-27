#include "game/app.h"

#include <cstdio>

#include <SDL3/SDL_init.h>
#include <SDL3/SDL_keyboard.h>
#include <SDL3/SDL_platform.h>
#include <SDL3/SDL_timer.h>

#include "core/log.h"
#include "core/text.h"
#include "version.h"

namespace sc {

namespace {

// Settings changes (window moved, mode switched) are saved in groups, a
// little after the last change, and always on exit.
constexpr std::uint64_t kSettingsSaveDelayNs = 2'000'000'000;

// While minimized, wake up this often to keep the simulation ticking.
constexpr std::int32_t kMinimizedWaitMs = 50;

// Placeholder sky color until the 3D renderer exists (phase 3).
constexpr ClearColor kClearColor{0.36f, 0.52f, 0.66f};

}  // namespace

int App::run() {
    if (!init()) {
        shutdown();
        return 1;
    }
    last_frame_ns_ = SDL_GetTicksNS();
    while (running_) {
        frame();
    }
    shutdown();
    return 0;
}

bool App::init() {
    (void)SDL_SetAppMetadata("SalvaCiudad", SC_VERSION_STRING, "io.github.salva.salvaciudad");
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        // No log folder yet. Fatal error dialogs arrive with the language
        // files in phase 2.
        std::fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return false;
    }
    sdl_ready_ = true;

    paths_ = resolve_data_paths();
    if (!paths_) {
        std::fprintf(stderr, "Cannot create the user data folder: %s\n", SDL_GetError());
        return false;
    }

    log::Options log_options;
#ifndef NDEBUG
    log_options.echo_to_stderr = true;
    log_options.min_level = log::Level::Debug;
#endif
    if (!log::open(paths_->logs_dir(), log_options)) {
        std::fprintf(stderr, "Cannot open the log file; continuing without it\n");
    }
    log::info("SalvaCiudad {} starting on {}", SC_VERSION_STRING, SDL_GetPlatform());
    log::info("data: {} mode", paths_->portable ? "portable" : "per-user");

    settings_.emplace(paths_->settings_file());
    const SettingsLoadReport report = settings_->load();
    // The report is shown to the player from phase 2 on (it needs the
    // language files); for now it goes to the log only.
    if (report.quarantined || report.read_only || report.ignored_fields > 0) {
        log::warn("settings: quarantined={} read_only={} ignored={}", report.quarantined, report.read_only,
                  report.ignored_fields);
    }

    const DisplaySettings& display = settings_->settings().display;
    if (display.mode != WindowMode::Windowed) {
        last_fullscreen_mode_ = display.mode;
    }
    if (!window_.create("SalvaCiudad", display)) {
        return false;
    }
    if (!gpu_.create(window_.sdl(), display.vsync)) {
        return false;
    }
    return true;
}

void App::shutdown() {
    if (settings_) {
        save_settings_if_due(true);
    }
    gpu_.destroy();
    window_.destroy();
    if (sdl_ready_) {
        SDL_Quit();
        sdl_ready_ = false;
    }
    log::info("SalvaCiudad stopped");
    log::close();
}

void App::handle_event(const SDL_Event& event) {
    switch (event.type) {
        case SDL_EVENT_QUIT:
            running_ = false;
            return;
        case SDL_EVENT_KEY_DOWN:
            if (event.key.repeat) {
                return;
            }
            // Temporary shortcuts until the input bindings arrive in phase 2.
            if (event.key.key == SDLK_F11) {
                // Cycle: windowed -> borderless -> fullscreen -> windowed.
                const WindowMode next = window_.mode() == WindowMode::Windowed     ? WindowMode::Borderless
                                        : window_.mode() == WindowMode::Borderless ? WindowMode::Fullscreen
                                                                                   : WindowMode::Windowed;
                set_window_mode(next);
            } else if (event.key.key == SDLK_RETURN && (event.key.mod & SDL_KMOD_ALT) != 0) {
                set_window_mode(window_.mode() == WindowMode::Windowed ? last_fullscreen_mode_
                                                                       : WindowMode::Windowed);
            }
            return;
        default:
            break;
    }
    if (event.type >= SDL_EVENT_WINDOW_FIRST && event.type <= SDL_EVENT_WINDOW_LAST) {
        if (window_.track_event(event, settings_->settings().display)) {
            mark_settings_dirty();
        }
    }
}

void App::set_window_mode(WindowMode mode) {
    DisplaySettings& display = settings_->settings().display;
    DisplaySettings wanted = display;
    wanted.mode = mode;
    if (!window_.apply(wanted)) {
        // Put back whatever mode was working.
        (void)window_.apply(display);
        return;
    }
    display.mode = mode;
    if (mode != WindowMode::Windowed) {
        last_fullscreen_mode_ = mode;
    }
    mark_settings_dirty();
}

void App::mark_settings_dirty() {
    if (settings_dirty_since_ns_ == 0) {
        settings_dirty_since_ns_ = SDL_GetTicksNS();
    }
}

void App::save_settings_if_due(bool force) {
    if (settings_dirty_since_ns_ == 0) {
        return;
    }
    if (!force && SDL_GetTicksNS() - settings_dirty_since_ns_ < kSettingsSaveDelayNs) {
        return;
    }
    settings_dirty_since_ns_ = 0;
    (void)settings_->save();
}

void App::frame() {
    SDL_Event event;
    if (window_.minimized()) {
        if (SDL_WaitEventTimeout(&event, kMinimizedWaitMs)) {
            handle_event(event);
        }
    }
    while (SDL_PollEvent(&event)) {
        handle_event(event);
    }

    const std::uint64_t now = SDL_GetTicksNS();
    const std::uint64_t elapsed = now - last_frame_ns_;
    last_frame_ns_ = now;

    const int ticks = clock_.advance(static_cast<std::int64_t>(elapsed));
    for (int i = 0; i < ticks; ++i) {
        // The deterministic simulation plugs in here (phase 5).
    }

    if (!window_.minimized()) {
        (void)gpu_.clear_frame(kClearColor);
    }
    save_settings_if_due(false);

    const DisplaySettings& display = settings_->settings().display;
    if (display.fps_limit > 0 && !display.vsync) {
        const std::uint64_t budget = 1'000'000'000ull / static_cast<std::uint64_t>(display.fps_limit);
        const std::uint64_t spent = SDL_GetTicksNS() - now;
        if (spent < budget) {
            SDL_DelayPrecise(budget - spent);
        }
    }
}

}  // namespace sc
