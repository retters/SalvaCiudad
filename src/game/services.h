// What the menus need from the application, as an interface so screens do
// not depend on the window, the GPU or SDL directly.
#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "game/settings.h"
#include "ui/font_library.h"

namespace sc {

struct Resolution {
    int width = 0;
    int height = 0;
    bool operator==(const Resolution&) const = default;
};

class Services {
public:
    virtual ~Services() = default;

    [[nodiscard]] virtual Settings& settings() = 0;
    // Schedules saving the settings (grouped, see App).
    virtual void settings_changed() = 0;

    // Switches window mode, monitor or resolution. Returns false if the
    // system refused; the previous state is then restored.
    virtual bool apply_display(const DisplaySettings& display) = 0;
    virtual void apply_vsync() = 0;
    virtual void apply_language() = 0;
    virtual void apply_font() = 0;

    [[nodiscard]] virtual std::vector<std::string> monitor_names() = 0;
    // Exclusive fullscreen resolutions of a monitor, largest first.
    [[nodiscard]] virtual std::vector<Resolution> fullscreen_resolutions(const std::string& monitor) = 0;
    [[nodiscard]] virtual const ui::FontLibrary& fonts() const = 0;

    virtual void open_data_folder() = 0;
    virtual void request_quit() = 0;
};

}  // namespace sc
