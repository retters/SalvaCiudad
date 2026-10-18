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

// A look of the logo for a fresh visit to the main menu (decision D-RENAME-05): any of
// `count` from `random`, but never `current` again when there is another (current -1: none yet).
[[nodiscard]] int pick_logo_style(int current, int count, std::uint64_t random);

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
    // Developer tools (F7 in the menus): the next look of the logo, named in a toast.
    void cycle_logo_style();
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

    // Phase 126: a menu panel shown with the next frame, in the middle over a
    // veil (or at height `y`, in pixels, without the veil).
    void menu(const std::string& id, ThingRows rows, float width = 520.0f, float y = -1.0f);
    // Phase 126: the rows of a menu panel last given ("main", "game_menu",
    // "settings"...), for the tests; null if it is not shown.
    [[nodiscard]] const ThingRows* menu_rows(const std::string& id) const { return menus_.rows(id); }

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
    bool leave_pending_ = false;  // Phase 125: "Leave" was pressed in the end panel.
    void load_screen(ui::Context& ctx, bool modal);
    void game_keys(ui::Context& ctx);
    [[nodiscard]] std::string camera_line() const;

    void main_menu(ui::Context& ctx);
    void draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                   bool draw);
    // The logo's glows and rule as one image, rebuilt only when its key changes.
    struct LogoGlowKey {
        int style = 0;
        int name_px = 0;
        int small_px = 0;
        int frac_x = 0;  // Sub-pixel position, in 64ths.
        int frac_y = 0;
        std::string small;
        std::string name;
        bool operator==(const LogoGlowKey&) const = default;
    };
    struct LogoGlowLayout {  // Positions relative to the image's top-left corner.
        ui::TextStyle name_style;
        ui::TextStyle small_style;
        const std::vector<std::string_view>* letters = nullptr;
        std::string_view name;
        float tracking = 0.0f;
        float small_w = 0.0f;
        float name_w = 0.0f;
        float block_h = 0.0f;
        int pad = 0;
        float center_x = 0.0f;
        float small_y = 0.0f;
        float name_x = 0.0f;
        float name_y = 0.0f;
        float rule_y = 0.0f;
        float rule_h = 0.0f;
    };
    struct LogoGlow {
        int w = 0;
        int h = 0;
        std::vector<std::uint8_t> rgba;
    };
    [[nodiscard]] static LogoGlow build_logo_glow(const ui::TextRenderer& text, const LogoGlowLayout& layout,
                                                  int style_index);
    std::optional<LogoGlowKey> logo_glow_key_;
    LogoGlow logo_glow_;
    int logo_style_ = -1;  // Index into the styles in ui_host.cpp; -1 until the menu first shows.
    std::uint64_t logo_random_ = 0;  // Seeded at start, stepped for every pick.
    // The screen of the previous frame; none on the first. Coming to the main menu from
    // nothing (the game starts) or from the map (a game was left) picks another logo.
    std::optional<Screen> last_screen_;
    void message_dialog(ui::Context& ctx);
    // Phase 76: who may come into the game (in the game menu).
    void access_dialog(ui::Context& ctx);
    bool access_dialog_ = false;
    bool access_open_ = true;
    bool access_join_ = true;
    bool access_found_ = true;
    bool access_watch_ = true;
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
    // Phase 126: the menus and screens out of a game (and the game menu),
    // as RmlUi panels of rows (ui_host_menus.cpp).
    RmlPanels menus_{services_};
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
