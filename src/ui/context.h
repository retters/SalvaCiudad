// The frame of the interface drawn by the game itself (phase 127): the
// input of the frame, the interface scale and a draw list with the text
// renderer, which the logo, the veils behind the menus and the developer
// tools use. The widgets of the old immediate-mode interface are gone: every
// screen, window and panel is RmlUi's (src/ui/rml, data/ui).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include <SDL3/SDL_scancode.h>

#include "ui/draw_list.h"
#include "ui/text.h"

namespace sc::ui {

struct Input {
    float mouse_x = -1.0f;
    float mouse_y = -1.0f;
    bool mouse_down = false;      // Left button held.
    bool mouse_pressed = false;   // Left button went down this frame.
    bool mouse_released = false;  // Left button went up this frame.
    float wheel = 0.0f;           // Positive scrolls up.
    std::vector<SDL_Scancode> keys;  // Keys pressed this frame, including repeats.
    std::string text;                // Text typed this frame (UTF-8).

    [[nodiscard]] bool key(SDL_Scancode k) const;
};

// The colors and sizes of what the game draws itself.
struct Theme {
    Color background = Color::rgb(0x1E2A33);
    Color text = Color::rgb(0xF2E8D5);
    Color text_dim = Color::rgb(0xB9AC94);
    Color accent = Color::rgb(0xD9A441);
    Color danger = Color::rgb(0xC0583F);
    Color overlay = Color::rgb(0x000000, 150);

    // Font sizes in design units.
    int small = 16;
    int body = 20;
    int heading = 26;
    int title = 34;
};

class Context {
public:
    explicit Context(TextRenderer& text) : text_(text) {}

    void begin_frame(const Input& input, float width, float height, float scale, std::uint64_t now_ns,
                     float white_u, float white_v);
    void end_frame() {}

    // While blocked (a menu is open over the game), the game's own keys and
    // clicks are ignored.
    void set_input_blocked(bool blocked) { blocked_ = blocked; }
    [[nodiscard]] bool input_blocked() const { return blocked_; }

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

private:
    TextRenderer& text_;
    DrawList draw_;
    Theme theme_;
    Input input_;
    float width_ = 0.0f;
    float height_ = 0.0f;
    float scale_ = 1.0f;
    std::uint64_t now_ns_ = 0;
    bool blocked_ = false;
};

}  // namespace sc::ui
