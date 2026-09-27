// Main game window: fullscreen, windowed and borderless modes, switchable at
// run time, remembering the windowed size and position.
#pragma once

#include <SDL3/SDL_events.h>
#include <SDL3/SDL_video.h>

#include "game/settings.h"

namespace sc {

class Window {
public:
    Window() = default;
    ~Window();
    Window(const Window&) = delete;
    Window& operator=(const Window&) = delete;

    // Creates the window hidden, applies the mode in `display` and shows it.
    bool create(const char* title, const DisplaySettings& display);
    void destroy();

    // Switches to `display.mode`. Returns false if SDL refused; the window
    // then stays in a usable state.
    bool apply(const DisplaySettings& display);

    // Updates the windowed geometry and the monitor in `display` from window
    // events. Returns true if `display` changed.
    bool track_event(const SDL_Event& event, DisplaySettings& display);

    [[nodiscard]] SDL_Window* sdl() const { return window_; }
    [[nodiscard]] WindowMode mode() const { return mode_; }
    [[nodiscard]] bool minimized() const;

private:
    SDL_Window* window_ = nullptr;
    WindowMode mode_ = WindowMode::Windowed;
};

// The display whose name matches `name`, or the primary display.
[[nodiscard]] SDL_DisplayID find_display(const std::string& name);

}  // namespace sc
