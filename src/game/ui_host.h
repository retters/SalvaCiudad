// Owns the menu screens and the dialogs shown over them: messages, the
// "keep these display settings?" countdown and notices.
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "game/new_game_screen.h"
#include "game/services.h"
#include "game/settings_screen.h"
#include "ui/context.h"

namespace sc {

class UiHost {
public:
    explicit UiHost(Services& services);

    void frame(ui::Context& ctx);

    // A dialog with a title, a text and an OK button.
    void show_message(std::string title, std::string body);
    // A dismissable notice on the main menu (for example, settings problems).
    void add_notice(std::string text);

    // Applies a display change and, if it worked, asks the player to keep it
    // within 15 seconds or reverts it.
    void change_display(const DisplaySettings& wanted);

    // True while a screen wants raw keys (key binding capture), so global
    // shortcuts must not act.
    [[nodiscard]] bool wants_keyboard() const;

    void open_settings() { screen_ = Screen::Settings; }

    // What the 3D view behind the interface should show.
    enum class SceneMode : std::uint8_t { None, MenuBackground, TestScene, Map };
    [[nodiscard]] SceneMode scene_mode() const;

private:
    enum class Screen : std::uint8_t { MainMenu, Settings, TestScene, NewGame, Generating, MapView };

    void test_scene_hud(ui::Context& ctx);
    void generating_screen(ui::Context& ctx, bool modal);
    void map_hud(ui::Context& ctx);
    [[nodiscard]] std::string camera_line() const;

    void main_menu(ui::Context& ctx);
    void draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                   bool draw);
    void message_dialog(ui::Context& ctx);
    void display_confirm_dialog(ui::Context& ctx);
    [[nodiscard]] bool modal_open() const;

    Services& services_;
    SettingsScreen settings_screen_;
    NewGameScreen new_game_;
    Screen screen_ = Screen::MainMenu;

    struct Message {
        std::string title;
        std::string body;
    };
    std::vector<Message> messages_;
    std::vector<std::string> notices_;

    struct PendingDisplay {
        DisplaySettings previous;
        std::uint64_t deadline_ns = 0;
        bool started = false;
    };
    std::optional<PendingDisplay> pending_display_;
};

}  // namespace sc
