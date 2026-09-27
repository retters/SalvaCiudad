// What the menus need from the application, as an interface so screens do
// not depend on the window, the GPU or SDL directly.
#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "game/camera.h"
#include "game/map_generation.h"
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
    virtual void apply_graphics() = 0;
    virtual void apply_language() = 0;
    virtual void apply_font() = 0;

    [[nodiscard]] virtual std::vector<std::string> monitor_names() = 0;
    // Exclusive fullscreen resolutions of a monitor, largest first.
    [[nodiscard]] virtual std::vector<Resolution> fullscreen_resolutions(const std::string& monitor) = 0;
    [[nodiscard]] virtual const ui::FontLibrary& fonts() const = 0;

    // True when the 3D test scene loaded and can be shown.
    [[nodiscard]] virtual bool scene_available() const = 0;
    [[nodiscard]] virtual CameraMode camera_mode() const = 0;

    // A new map is generated in the background; the screens poll its state.
    virtual void start_map_generation(const sim::MapSettings& settings) = 0;
    [[nodiscard]] virtual MapGenStatus map_generation_status() const = 0;
    virtual void cancel_map_generation() = 0;
    // Shows the generated map in the 3D view; false if it could not.
    virtual bool enter_generated_map() = 0;
    virtual void leave_map() = 0;
    // The map being shown, if any.
    [[nodiscard]] virtual const sim::MapData* current_map() const = 0;

    virtual void open_data_folder() = 0;
    virtual void request_quit() = 0;
};

}  // namespace sc
