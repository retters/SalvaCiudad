#include "platform/window.h"

#include <SDL3/SDL_error.h>

#include "core/log.h"

namespace sc {

namespace {

// A saved windowed position is used only if at least this much of the
// window's title area lands inside a display.
constexpr int kMinVisiblePixels = 64;

bool position_is_visible(int x, int y, int w) {
    int count = 0;
    SDL_DisplayID* displays = SDL_GetDisplays(&count);
    if (displays == nullptr) {
        return false;
    }
    bool visible = false;
    const SDL_Rect title_area{x, y, w, kMinVisiblePixels};
    for (int i = 0; i < count && !visible; ++i) {
        SDL_Rect bounds{};
        SDL_Rect overlap{};
        if (SDL_GetDisplayUsableBounds(displays[i], &bounds) &&
            SDL_GetRectIntersection(&title_area, &bounds, &overlap)) {
            visible = overlap.w >= kMinVisiblePixels && overlap.h >= kMinVisiblePixels / 2;
        }
    }
    SDL_free(displays);
    return visible;
}

const char* display_name(SDL_DisplayID id) {
    const char* name = SDL_GetDisplayName(id);
    return name != nullptr ? name : "";
}

}  // namespace

SDL_DisplayID find_display(const std::string& name) {
    if (!name.empty()) {
        int count = 0;
        SDL_DisplayID* displays = SDL_GetDisplays(&count);
        SDL_DisplayID found = 0;
        for (int i = 0; displays != nullptr && i < count && found == 0; ++i) {
            if (name == display_name(displays[i])) {
                found = displays[i];
            }
        }
        SDL_free(displays);
        if (found != 0) {
            return found;
        }
    }
    return SDL_GetPrimaryDisplay();
}

Window::~Window() {
    destroy();
}

bool Window::create(const char* title, const DisplaySettings& display) {
    const SDL_WindowFlags flags = SDL_WINDOW_HIDDEN | SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY;
    window_ = SDL_CreateWindow(title, display.window_width, display.window_height, flags);
    if (window_ == nullptr) {
        log::error("window: SDL_CreateWindow failed: {}", SDL_GetError());
        return false;
    }
    SDL_SetWindowMinimumSize(window_, settings_limits::kMinWindowSize, settings_limits::kMinWindowSize / 2);
    if (!apply(display)) {
        log::warn("window: could not apply the saved mode, falling back to windowed");
        DisplaySettings fallback = display;
        fallback.mode = WindowMode::Windowed;
        (void)apply(fallback);
    }
    if (!SDL_ShowWindow(window_)) {
        log::error("window: SDL_ShowWindow failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

void Window::destroy() {
    if (window_ != nullptr) {
        SDL_DestroyWindow(window_);
        window_ = nullptr;
    }
}

bool Window::apply(const DisplaySettings& display) {
    // When the window already exists, fullscreen goes to the display it is
    // on; at startup, to the saved one.
    SDL_DisplayID target = SDL_GetDisplayForWindow(window_);
    if (target == 0 || (SDL_GetWindowFlags(window_) & SDL_WINDOW_HIDDEN) != 0) {
        target = find_display(display.monitor);
    }

    bool ok = true;
    switch (display.mode) {
        case WindowMode::Windowed: {
            ok = SDL_SetWindowFullscreen(window_, false);
            (void)SDL_SyncWindow(window_);
            ok = ok && SDL_SetWindowSize(window_, display.window_width, display.window_height);
            if (display.window_x && display.window_y &&
                position_is_visible(*display.window_x, *display.window_y, display.window_width)) {
                ok = ok && SDL_SetWindowPosition(window_, *display.window_x, *display.window_y);
            } else {
                ok = ok && SDL_SetWindowPosition(window_, static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)),
                                                 static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)));
            }
            if (ok && display.window_maximized) {
                ok = SDL_MaximizeWindow(window_);
            }
            break;
        }
        case WindowMode::Borderless: {
            // Fullscreen at the desktop resolution: no display mode change.
            ok = SDL_SetWindowFullscreenMode(window_, nullptr);
            ok = ok && SDL_SetWindowPosition(window_, static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)),
                                             static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)));
            ok = ok && SDL_SetWindowFullscreen(window_, true);
            break;
        }
        case WindowMode::Fullscreen: {
            SDL_DisplayMode mode{};
            bool have_mode = false;
            if (display.fullscreen_width > 0 && display.fullscreen_height > 0) {
                have_mode = SDL_GetClosestFullscreenDisplayMode(target, display.fullscreen_width,
                                                                display.fullscreen_height, 0.0f, true, &mode);
            }
            if (!have_mode) {
                const SDL_DisplayMode* desktop = SDL_GetDesktopDisplayMode(target);
                if (desktop != nullptr) {
                    mode = *desktop;
                    have_mode = true;
                }
            }
            ok = have_mode;
            ok = ok && SDL_SetWindowPosition(window_, static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)),
                                             static_cast<int>(SDL_WINDOWPOS_CENTERED_DISPLAY(target)));
            ok = ok && SDL_SetWindowFullscreenMode(window_, &mode);
            ok = ok && SDL_SetWindowFullscreen(window_, true);
            break;
        }
    }
    if (!SDL_SyncWindow(window_)) {
        log::debug("window: SDL_SyncWindow timed out");
    }
    if (!ok) {
        log::error("window: switching to {} failed: {}", window_mode_to_string(display.mode), SDL_GetError());
        return false;
    }
    mode_ = display.mode;
    log::info("window: mode {} on display '{}'", window_mode_to_string(mode_), display_name(target));
    return true;
}

bool Window::track_event(const SDL_Event& event, DisplaySettings& display) {
    if (window_ == nullptr || event.window.windowID != SDL_GetWindowID(window_)) {
        return false;
    }
    const SDL_WindowFlags flags = SDL_GetWindowFlags(window_);
    const bool windowed = mode_ == WindowMode::Windowed && (flags & SDL_WINDOW_FULLSCREEN) == 0;
    const DisplaySettings before = display;

    switch (event.type) {
        case SDL_EVENT_WINDOW_MOVED:
            if (windowed && (flags & (SDL_WINDOW_MAXIMIZED | SDL_WINDOW_MINIMIZED)) == 0) {
                display.window_x = event.window.data1;
                display.window_y = event.window.data2;
            }
            break;
        case SDL_EVENT_WINDOW_RESIZED:
            if (windowed && (flags & (SDL_WINDOW_MAXIMIZED | SDL_WINDOW_MINIMIZED)) == 0) {
                display.window_width = event.window.data1;
                display.window_height = event.window.data2;
            }
            break;
        case SDL_EVENT_WINDOW_MAXIMIZED:
            if (windowed) {
                display.window_maximized = true;
            }
            break;
        case SDL_EVENT_WINDOW_RESTORED:
            if (windowed) {
                display.window_maximized = false;
            }
            break;
        case SDL_EVENT_WINDOW_DISPLAY_CHANGED:
            display.monitor = display_name(SDL_GetDisplayForWindow(window_));
            break;
        default:
            break;
    }
    return !(display == before);
}

bool Window::minimized() const {
    return window_ != nullptr && (SDL_GetWindowFlags(window_) & SDL_WINDOW_MINIMIZED) != 0;
}

}  // namespace sc
