// The Settings screen: tabs for display, graphics, audio, controls,
// interface, language and game. Every change applies and saves at once.
// Phase 126: an RmlUi menu panel of rows (thing_rows.h).
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "game/input_actions.h"
#include "game/services.h"
#include "game/thing_rows.h"
#include "ui/context.h"

namespace sc {

class UiHost;

class SettingsScreen {
public:
    explicit SettingsScreen(Services& services) : services_(services) {}

    // Returns false when the player leaves the screen.
    bool frame(ui::Context& ctx, UiHost& host, bool input_blocked);
    // The rows of the tab shown (the tests press their buttons).
    [[nodiscard]] ThingRows rows(UiHost& host);

    [[nodiscard]] bool capturing_key() const { return capture_.has_value(); }
    // A key pressed while a binding waits for one (as frame() does).
    void key_pressed(SDL_Scancode key);

    enum class Tab : std::uint8_t { Display, Graphics, Audio, Controls, Interface, Language, Game, Count };
    void show_tab(Tab tab) { tab_ = tab; }

private:
    void tab_display(ThingRows& out, UiHost& host);
    void tab_graphics(ThingRows& out);
    void tab_audio(ThingRows& out);
    void tab_controls(ThingRows& out);
    void tab_interface(ThingRows& out);
    void tab_language(ThingRows& out);
    void tab_game(ThingRows& out);
    void restore_tab_defaults(UiHost& host);

    Services& services_;
    Tab tab_ = Tab::Display;
    bool leave_ = false;
    // Sliders write here; the change is applied when it differs.
    std::vector<int> values_;

    struct Capture {
        Action action;
        std::size_t slot;
    };
    std::optional<Capture> capture_;
    std::string binding_notice_;
};

}  // namespace sc
