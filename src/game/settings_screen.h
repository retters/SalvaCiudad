// The Settings screen: tabs for display, graphics, audio, controls,
// interface, language and game. Every change applies and saves at once.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "game/input_actions.h"
#include "game/services.h"
#include "ui/context.h"

namespace sc {

class UiHost;

class SettingsScreen {
public:
    explicit SettingsScreen(Services& services) : services_(services) {}

    // Returns false when the player leaves the screen.
    bool frame(ui::Context& ctx, UiHost& host, bool input_blocked);

    [[nodiscard]] bool capturing_key() const { return capture_.has_value(); }

private:
    enum class Tab : std::uint8_t { Display, Graphics, Audio, Controls, Interface, Language, Game, Count };

    struct Row {
        ui::Rect label;
        ui::Rect control;
    };
    // Lays out one "label | control" row (stacked when narrow) and draws the
    // label with its tooltip.
    Row row(ui::Context& ctx, float x, float& y, float width, std::string_view label, std::string_view tooltip);
    void section(ui::Context& ctx, float x, float& y, float width, std::string_view title);

    void tab_display(ui::Context& ctx, UiHost& host, float x, float& y, float w);
    void tab_graphics(ui::Context& ctx, float x, float& y, float w);
    void tab_audio(ui::Context& ctx, float x, float& y, float w);
    void tab_controls(ui::Context& ctx, float x, float& y, float w);
    void tab_interface(ui::Context& ctx, float x, float& y, float w);
    void tab_language(ui::Context& ctx, float x, float& y, float w);
    void tab_game(ui::Context& ctx, float x, float& y, float w);
    void restore_tab_defaults(UiHost& host);
    void handle_key_capture(ui::Context& ctx);
    void capture_dialog(ui::Context& ctx);

    Services& services_;
    Tab tab_ = Tab::Display;

    struct Capture {
        Action action;
        std::size_t slot;
    };
    std::optional<Capture> capture_;
    std::string binding_notice_;
};

}  // namespace sc
