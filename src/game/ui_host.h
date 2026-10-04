// Owns the menu screens and the dialogs shown over them: messages, the
// "keep these display settings?" countdown and notices.
#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "game/game_hud.h"
#include "script/tutorial_script.h"
#include "game/mods_screen.h"
#include "game/multiplayer_screens.h"
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
    // A short line at the top of the screen that goes away by itself.
    void toast(std::string text);
    // A game event for the notifications and the event log.
    void notify(std::string text, bool has_pos, float x, float z, const sim::Calendar& when, std::uint64_t now_ns) {
        hud_.notify(std::move(text), has_pos, x, z, when, now_ns);
    }

    // Applies a display change and, if it worked, asks the player to keep it
    // within 15 seconds or reverts it.
    void change_display(const DisplaySettings& wanted);

    // True while a screen wants raw keys (key binding capture), so global
    // shortcuts must not act.
    [[nodiscard]] bool wants_keyboard() const;

    void open_settings() {
        settings_return_ = Screen::MainMenu;
        screen_ = Screen::Settings;
    }

    // True while a menu covers the 3D view (the in-game menu, or settings
    // opened from it): the camera must not move.
    [[nodiscard]] bool scene_paused() const;
    // True while the game must not advance: paused by the player, or a
    // menu is open over a single-player game.
    [[nodiscard]] bool game_paused() const;
    // Generates a map and shows it, as "Generate" in the new game form does
    // (phase 38, for `--reporte`).
    void generate(const sim::MapSettings& settings, const sim::GameRules& rules) {
        services_.start_map_generation(settings, rules);
        screen_ = Screen::Generating;
    }
    // A game was loaded from outside the menus (quick load): show it.
    void show_game() {
        screen_ = Screen::MapView;
        game_menu_open_ = false;
    }

    // What the 3D view behind the interface should show.
    enum class SceneMode : std::uint8_t { None, MenuBackground, Map };
    [[nodiscard]] SceneMode scene_mode() const;

private:
    enum class Screen : std::uint8_t { MainMenu, Settings, NewGame, Generating, MapView, Mods, Load, Join, Lobby };

    void generating_screen(ui::Context& ctx, bool modal);
    void map_hud(ui::Context& ctx);
    void game_menu(ui::Context& ctx);
    void end_panel(ui::Context& ctx);  // The game is over: who won, the scores.
    // The tutorial (section 6.5).
    struct TutorialRun {
        std::size_t def = 0;
        std::size_t step = 0;
        std::array<float, 3> camera{};  // Where the camera was when the step began.
        int speed = 1;
        bool step_started = false;
        std::uint64_t next_lua_ns = 0;
        std::string error;
    };
    std::optional<TutorialRun> tutorial_;
    std::unique_ptr<script::TutorialScript> tutorial_lua_;
    void start_tutorial(std::size_t index);
    void tutorial_panel(ui::Context& ctx);
    [[nodiscard]] bool tutorial_step_done(const sim::TutorialStep& step, std::uint64_t now_ns);
    bool end_seen_ = false;
    void load_screen(ui::Context& ctx, bool modal);
    void game_keys(ui::Context& ctx);
    [[nodiscard]] std::string camera_line() const;

    void main_menu(ui::Context& ctx);
    void draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                   bool draw);
    void message_dialog(ui::Context& ctx);
    // Phase 76: who may come into the game (in the game menu).
    void access_dialog(ui::Context& ctx);
    bool access_dialog_ = false;
    bool access_open_ = true;
    bool access_join_ = true;
    bool access_found_ = true;
    void display_confirm_dialog(ui::Context& ctx);
    [[nodiscard]] bool modal_open() const;

    Services& services_;
    SettingsScreen settings_screen_;
    NewGameScreen new_game_;
    ModsScreen mods_screen_;
    Screen screen_ = Screen::MainMenu;
    Screen settings_return_ = Screen::MainMenu;  // Where closing settings goes.
    Screen load_return_ = Screen::MainMenu;      // Where closing the load list goes.
    bool game_menu_open_ = false;
    GameHud hud_;
    JoinScreen join_;
    LobbyScreen lobby_screen_;
    bool host_new_game_ = false;  // The new game screen is choosing a multiplayer map.
    void follow_network();
    int last_speed_ = 4;  // Speed to go back to after a pause (quarters; 4 is x1).
    std::vector<save::Entry> saves_;  // The load list, read when it opens.

    struct Message {
        std::string title;
        std::string body;
    };
    std::vector<Message> messages_;
    std::vector<std::string> notices_;
    std::string toast_;
    std::uint64_t toast_since_ns_ = 0;  // 0: shown from the next frame.
    void draw_toast(ui::Context& ctx);

    struct PendingDisplay {
        DisplaySettings previous;
        std::uint64_t deadline_ns = 0;
        bool started = false;
    };
    std::optional<PendingDisplay> pending_display_;
};

}  // namespace sc
