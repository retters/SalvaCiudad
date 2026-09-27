// Immediate-mode interface: each frame the screens call widget functions,
// which draw themselves and report interaction. Sizes are given in design
// units and multiplied by the interface scale.
#pragma once

#include <cstdint>
#include <functional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include <SDL3/SDL_scancode.h>

#include "ui/draw_list.h"
#include "ui/text.h"

namespace sc::ui {

using Id = std::uint64_t;

struct Input {
    float mouse_x = -1.0f;
    float mouse_y = -1.0f;
    bool mouse_down = false;      // Left button held.
    bool mouse_pressed = false;   // Left button went down this frame.
    bool mouse_released = false;  // Left button went up this frame.
    float wheel = 0.0f;           // Positive scrolls up.
    std::vector<SDL_Scancode> keys;  // Keys pressed this frame, including repeats.

    [[nodiscard]] bool key(SDL_Scancode k) const;
};

struct Theme {
    Color background = Color::rgb(0x1E2A33);
    Color panel = Color::rgb(0x2B2620, 235);
    Color panel_border = Color::rgb(0x8C7651);
    Color text = Color::rgb(0xF2E8D5);
    Color text_dim = Color::rgb(0xB9AC94);
    Color text_disabled = Color::rgb(0x7A7163);
    Color button = Color::rgb(0x4A3F31);
    Color button_hover = Color::rgb(0x62533E);
    Color button_active = Color::rgb(0x3A3127);
    Color accent = Color::rgb(0xD9A441);
    Color danger = Color::rgb(0xC0583F);
    Color tooltip = Color::rgb(0x15120E, 245);
    Color overlay = Color::rgb(0x000000, 150);

    // Font sizes in design units.
    int small = 16;
    int body = 20;
    int heading = 26;
    int title = 34;
};

enum class Align : std::uint8_t { Left, Center, Right };

class Context {
public:
    explicit Context(TextRenderer& text) : text_(text) {}

    void begin_frame(const Input& input, float width, float height, float scale, std::uint64_t now_ns,
                     float white_u, float white_v);
    // Draws the pending tooltip on top of everything.
    void end_frame();

    void set_tooltips(bool enabled, int delay_ms);

    // While blocked (a modal is open over the widgets being drawn), widgets
    // are drawn but ignore the mouse.
    void set_input_blocked(bool blocked) { blocked_ = blocked; }

    [[nodiscard]] float s(float design_units) const { return design_units * scale_; }
    [[nodiscard]] TextStyle style(int design_px, FontRole role = FontRole::Regular) const;
    [[nodiscard]] float scale() const { return scale_; }
    [[nodiscard]] float width() const { return width_; }
    [[nodiscard]] float height() const { return height_; }
    [[nodiscard]] const Theme& theme() const { return theme_; }
    [[nodiscard]] const Input& input() const { return input_; }
    [[nodiscard]] DrawList& draw() { return draw_; }
    [[nodiscard]] const DrawList& draw() const { return draw_; }
    [[nodiscard]] TextRenderer& text() { return text_; }
    [[nodiscard]] std::uint64_t now_ns() const { return now_ns_; }

    // Ids: hashed from a string within the current scope.
    [[nodiscard]] Id id(std::string_view name) const;
    void push_id(std::string_view name);
    void pop_id();

    // --- Drawing helpers -------------------------------------------------
    void panel(const Rect& r);
    // Single line, ellipsized to fit; vertically centered in `r`.
    void label(const Rect& r, std::string_view text, TextStyle style, Color color, Align align = Align::Left);
    // Wrapped paragraph starting at the top of `r`. Returns the height used.
    float paragraph(const Rect& r, std::string_view text, TextStyle style, Color color, Align align = Align::Left);
    [[nodiscard]] float paragraph_height(float width, std::string_view text, TextStyle style) const;

    // --- Widgets ---------------------------------------------------------
    // Registers a hover area with a tooltip, without other behavior.
    void tooltip_area(Id id, const Rect& r, std::string_view tooltip);

    bool button(Id id, const Rect& r, std::string_view label, std::string_view tooltip = {}, bool enabled = true,
                bool highlighted = false);
    bool checkbox(Id id, const Rect& r, bool& value, std::string_view tooltip = {}, bool enabled = true);
    // Integer slider with `step`; `format` makes the text shown on it.
    bool slider(Id id, const Rect& r, int& value, int min, int max, int step,
                const std::function<std::string(int)>& format, std::string_view tooltip = {}, bool enabled = true);
    // "<  option  >" selector. Returns true when `index` changed.
    bool selector(Id id, const Rect& r, int& index, std::span<const std::string> options,
                  std::string_view tooltip = {}, bool enabled = true);

    // Vertical scrolling region. Content is drawn with its top at the
    // returned y; call end_scroll with the content height.
    float begin_scroll(Id id, const Rect& viewport);
    void end_scroll(float content_height);

private:
    struct Interaction {
        bool hovered = false;
        bool held = false;
        bool clicked = false;
    };
    Interaction interact(Id id, const Rect& r, bool enabled, std::string_view tooltip);
    [[nodiscard]] bool mouse_in(const Rect& r) const;

    struct ScrollState {
        Id id = 0;
        float offset = 0.0f;
    };
    struct ActiveScroll {
        Id id = 0;
        Rect viewport;
    };
    ScrollState& scroll_state(Id id);

    TextRenderer& text_;
    DrawList draw_;
    Theme theme_;
    Input input_;
    float width_ = 0.0f;
    float height_ = 0.0f;
    float scale_ = 1.0f;
    std::uint64_t now_ns_ = 0;
    bool blocked_ = false;

    std::vector<Id> id_stack_;
    Id active_id_ = 0;    // Widget holding the mouse button.
    Id hovered_id_ = 0;   // Widget under the mouse this frame.
    Id tooltip_id_ = 0;   // Widget whose tooltip is being timed.
    std::uint64_t tooltip_since_ns_ = 0;
    Id frame_tooltip_id_ = 0;  // Widget with a tooltip under the mouse this frame.
    std::string frame_tooltip_text_;
    Rect frame_tooltip_anchor_;
    bool tooltips_enabled_ = true;
    std::uint64_t tooltip_delay_ns_ = 500'000'000;

    std::vector<ScrollState> scrolls_;
    std::vector<ActiveScroll> scroll_stack_;
};

}  // namespace sc::ui
