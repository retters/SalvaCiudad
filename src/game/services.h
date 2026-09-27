// What the menus need from the application, as an interface so screens do
// not depend on the window, the GPU or SDL directly.
#pragma once

#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

#include "game/camera.h"
#include "game/game_session.h"
#include "game/map_generation.h"
#include "game/settings.h"
#include "mods/mod_library.h"
#include "net/enet_link.h"
#include "net/lockstep.h"
#include "sim/content.h"
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
    virtual void start_map_generation(const sim::MapSettings& settings, const sim::GameRules& rules) = 0;
    [[nodiscard]] virtual MapGenStatus map_generation_status() const = 0;
    virtual void cancel_map_generation() = 0;
    // Shows the generated map in the 3D view; false if it could not.
    virtual bool enter_generated_map() = 0;
    virtual void leave_map() = 0;
    // The map being shown, if any.
    [[nodiscard]] virtual const sim::MapData* current_map() const = 0;

    virtual void open_data_folder() = 0;

    // Mods (section 7.13).
    [[nodiscard]] virtual mods::ModLibrary& mod_library() = 0;
    // Saves the choice of mods and rebuilds the game's content with them.
    virtual void apply_mods(const std::vector<std::string>& enabled) = 0;
    virtual void open_mods_folder() = 0;
    // The content of the loaded mods; never null after start-up.
    [[nodiscard]] virtual const sim::Content* content() const = 0;
    virtual void request_quit() = 0;

    // The village game being played, if any (phase 8).
    [[nodiscard]] virtual GameSession* session() = 0;
    // 0 pauses; 1..3.
    [[nodiscard]] virtual int game_speed() const = 0;
    virtual void set_game_speed(int speed) = 0;
    // Saves the game in the saves folder and tells the player how it went.
    virtual void save_game() = 0;
    [[nodiscard]] virtual std::vector<save::Entry> list_saves() = 0;
    // Loads a saved game and shows it. On failure the player is told why
    // and false is returned; a game being played is kept.
    virtual bool load_game(const std::filesystem::path& file) = 0;

    // Multiplayer (phase 9).
    // Opens a lobby as host with this map; false if the port is busy.
    virtual bool host_game(const sim::MapSettings& map, const sim::GameRules& rules) = 0;
    // Connects to a host; the lobby shows once it answers.
    virtual bool join_game(const std::string& address, std::uint16_t port) = 0;
    virtual void leave_network() = 0;
    [[nodiscard]] virtual net::NetSession* net() = 0;
    virtual void set_lan_search(bool on) = 0;
    [[nodiscard]] virtual std::vector<net::LanGame> lan_games() = 0;
    // The player's name: from the settings, or a default one.
    [[nodiscard]] virtual std::string player_name() const = 0;
};

}  // namespace sc
