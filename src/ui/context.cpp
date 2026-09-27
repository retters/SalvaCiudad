#include "ui/context.h"

#include <algorithm>
#include <cmath>

namespace sc::ui {

namespace {

// FNV-1a, mixed with the parent scope.
Id hash_id(std::string_view name, Id seed) {
    Id h = seed ^ 0xcbf29ce484222325ull;
    for (const char c : name) {
        h ^= static_cast<std::uint8_t>(c);
        h *= 0x100000001b3ull;
    }
    return h == 0 ? 1 : h;
}

}  // namespace

bool Input::key(SDL_Scancode k) const {
    return std::find(keys.begin(), keys.end(), k) != keys.end();
}

void Context::begin_frame(const Input& input, float width, float height, float scale, std::uint64_t now_ns,
                          float white_u, float white_v) {
    input_ = input;
    // A field that was not drawn last frame loses the keyboard.
    if (!focus_seen_) {
        focus_id_ = 0;
    }
    focus_seen_ = false;
    width_ = width;
    height_ = height;
    scale_ = scale;
    now_ns_ = now_ns;
    blocked_ = false;
    hovered_id_ = 0;
    id_stack_.clear();
    scroll_stack_.clear();
    frame_tooltip_id_ = 0;
    draw_.reset(width, height, white_u, white_v);
}

void Context::set_tooltips(bool enabled, int delay_ms) {
    tooltips_enabled_ = enabled;
    tooltip_delay_ns_ = static_cast<std::uint64_t>(std::max(0, delay_ms)) * 1'000'000ull;
}

TextStyle Context::style(int design_px, FontRole role) const {
    return {role, std::max(6, static_cast<int>(std::lround(static_cast<float>(design_px) * scale_)))};
}

Id Context::id(std::string_view name) const {
    return hash_id(name, id_stack_.empty() ? 0 : id_stack_.back());
}

void Context::push_id(std::string_view name) {
    id_stack_.push_back(id(name));
}

void Context::pop_id() {
    if (!id_stack_.empty()) {
        id_stack_.pop_back();
    }
}

bool Context::mouse_in(const Rect& r) const {
    return r.contains(input_.mouse_x, input_.mouse_y) && draw_.clip().contains(input_.mouse_x, input_.mouse_y);
}

Context::Interaction Context::interact(Id id, const Rect& r, bool enabled, std::string_view tooltip) {
    Interaction result;
    if (blocked_) {
        return result;
    }
    const bool inside = mouse_in(r);
    if (inside) {
        hovered_id_ = id;
        if (!tooltip.empty()) {
            frame_tooltip_id_ = id;
            frame_tooltip_text_ = std::string(tooltip);
            frame_tooltip_anchor_ = r;
        }
    }
    if (!enabled) {
        return result;
    }
    result.hovered = inside && (active_id_ == 0 || active_id_ == id);
    if (inside && input_.mouse_pressed) {
        active_id_ = id;
    }
    result.held = active_id_ == id && input_.mouse_down;
    result.clicked = active_id_ == id && input_.mouse_released && inside;
    return result;
}

void Context::tooltip_area(Id id, const Rect& r, std::string_view tooltip) {
    (void)interact(id, r, false, tooltip);
}

void Context::panel(const Rect& r) {
    draw_.rect(r, theme_.panel);
    draw_.rect_outline(r, theme_.panel_border, std::max(1.0f, std::round(s(1.5f))));
}

void Context::label(const Rect& r, std::string_view text, TextStyle st, Color color, Align align) {
    const std::string fitted = text_.ellipsize(st, text, r.w);
    const float w = text_.measure(st, fitted);
    const float lh = text_.line_height(st);
    float x = r.x;
    if (align == Align::Center) {
        x = r.x + (r.w - w) * 0.5f;
    } else if (align == Align::Right) {
        x = r.right() - w;
    }
    const float y = r.y + (r.h - lh) * 0.5f;
    text_.draw(draw_, st, std::round(x), std::round(y), fitted, color);
}

float Context::paragraph(const Rect& r, std::string_view text, TextStyle st, Color color, Align align) {
    const float lh = text_.line_height(st);
    float y = r.y;
    for (const std::string& line : text_.wrap(st, text, r.w)) {
        const float w = text_.measure(st, line);
        float x = r.x;
        if (align == Align::Center) {
            x = r.x + (r.w - w) * 0.5f;
        } else if (align == Align::Right) {
            x = r.right() - w;
        }
        text_.draw(draw_, st, std::round(x), std::round(y), line, color);
        y += lh;
    }
    return y - r.y;
}

float Context::paragraph_height(float width, std::string_view text, TextStyle st) const {
    return static_cast<float>(text_.wrap(st, text, width).size()) * text_.line_height(st);
}

bool Context::button(Id id, const Rect& r, std::string_view label_text, std::string_view tooltip, bool enabled,
                     bool highlighted) {
    const Interaction it = interact(id, r, enabled, tooltip);
    Color fill = theme_.button;
    if (!enabled) {
        fill = theme_.button.with_alpha(0.5f);
    } else if (it.held) {
        fill = theme_.button_active;
    } else if (it.hovered) {
        fill = theme_.button_hover;
    }
    draw_.rect(r, fill);
    const float border = std::max(1.0f, std::round(s(1.0f)));
    draw_.rect_outline(r, highlighted || it.hovered ? theme_.accent : theme_.panel_border, border);
    label(r.inset(s(8.0f)), label_text, style(theme_.body), enabled ? theme_.text : theme_.text_disabled,
          Align::Center);
    return it.clicked;
}

bool Context::checkbox(Id id, const Rect& r, bool& value, std::string_view tooltip, bool enabled) {
    const Interaction it = interact(id, r, enabled, tooltip);
    const float box = std::min(r.h, s(24.0f));
    const Rect b{r.x, r.y + (r.h - box) * 0.5f, box, box};
    draw_.rect(b, it.hovered ? theme_.button_hover : theme_.button);
    draw_.rect_outline(b, it.hovered ? theme_.accent : theme_.panel_border, std::max(1.0f, std::round(s(1.0f))));
    if (value) {
        draw_.rect(b.inset(std::round(box * 0.25f)), enabled ? theme_.accent : theme_.text_disabled);
    }
    if (it.clicked) {
        value = !value;
        return true;
    }
    return false;
}

bool Context::text_field(Id id, const Rect& r, std::string& value, std::size_t max_bytes, std::string_view tooltip,
                         std::string_view allowed) {
    const Interaction it = interact(id, r, true, tooltip);
    if (it.clicked && !blocked_) {
        focus_id_ = id;
    } else if (input_.mouse_pressed && !mouse_in(r) && focus_id_ == id) {
        focus_id_ = 0;
    }
    const bool focused = focus_id_ == id && !blocked_;
    bool changed = false;
    if (focused) {
        focus_seen_ = true;
        for (std::size_t i = 0; i < input_.text.size();) {
            // One UTF-8 sequence at a time.
            std::size_t len = 1;
            const auto c = static_cast<unsigned char>(input_.text[i]);
            if (c >= 0xF0) {
                len = 4;
            } else if (c >= 0xE0) {
                len = 3;
            } else if (c >= 0xC0) {
                len = 2;
            }
            const std::string_view ch = std::string_view(input_.text).substr(i, len);
            i += len;
            const bool printable = ch.size() > 1 || (ch[0] >= 0x20 && ch[0] != 0x7F);
            const bool ok = allowed.empty() ? printable : (ch.size() == 1 && allowed.find(ch[0]) != std::string_view::npos);
            if (ok && value.size() + ch.size() <= max_bytes) {
                value += ch;
                changed = true;
            }
        }
        for (const SDL_Scancode k : input_.keys) {
            if (k == SDL_SCANCODE_BACKSPACE && !value.empty()) {
                // Remove the whole last UTF-8 sequence.
                std::size_t cut = value.size() - 1;
                while (cut > 0 && (static_cast<unsigned char>(value[cut]) & 0xC0) == 0x80) {
                    --cut;
                }
                value.erase(cut);
                changed = true;
            } else if (k == SDL_SCANCODE_RETURN || k == SDL_SCANCODE_KP_ENTER || k == SDL_SCANCODE_ESCAPE ||
                       k == SDL_SCANCODE_TAB) {
                focus_id_ = 0;
            }
        }
    }
    draw_.rect(r, focused ? theme_.button_active : theme_.button);
    draw_.rect_outline(r, focused || it.hovered ? theme_.accent : theme_.panel_border,
                       std::max(1.0f, std::round(s(1.0f))));
    const TextStyle st = style(theme_.body);
    const float pad = s(8.0f);
    const Rect inner{r.x + pad, r.y, r.w - 2 * pad, r.h};
    label(inner, value, st, theme_.text);
    if (focused && (now_ns_ / 500'000'000ull) % 2 == 0) {
        const float x = std::min(inner.right() - 1.0f, inner.x + text_.measure(st, value) + 1.0f);
        const float h = text_.line_height(st);
        draw_.rect({std::round(x), std::round(r.y + (r.h - h) * 0.5f), std::max(1.0f, std::round(s(2.0f))), std::round(h)},
                   theme_.text);
    }
    return changed;
}

bool Context::slider(Id id, const Rect& r, int& value, int min, int max, int step,
                     const std::function<std::string(int)>& format, std::string_view tooltip, bool enabled) {
    const Interaction it = interact(id, r, enabled, tooltip);
    const int old = value;
    if (it.held && r.w > 0.0f && max > min) {
        const float t = std::clamp((input_.mouse_x - r.x) / r.w, 0.0f, 1.0f);
        const float raw = static_cast<float>(min) + t * static_cast<float>(max - min);
        const int stepped = min + static_cast<int>(std::lround((raw - static_cast<float>(min)) / static_cast<float>(step))) * step;
        value = std::clamp(stepped, min, max);
    }
    draw_.rect(r, enabled ? theme_.button_active : theme_.button_active.with_alpha(0.5f));
    const float t = max > min ? static_cast<float>(value - min) / static_cast<float>(max - min) : 0.0f;
    draw_.rect({r.x, r.y, std::round(r.w * t), r.h},
               enabled ? (it.hovered || it.held ? theme_.accent : theme_.accent.with_alpha(0.75f))
                       : theme_.text_disabled.with_alpha(0.5f));
    draw_.rect_outline(r, theme_.panel_border, std::max(1.0f, std::round(s(1.0f))));
    label(r.inset(s(4.0f)), format(value), style(theme_.body), enabled ? theme_.text : theme_.text_disabled,
          Align::Center);
    return value != old;
}

bool Context::selector(Id id, const Rect& r, int& index, std::span<const std::string> options,
                       std::string_view tooltip, bool enabled) {
    if (options.empty()) {
        return false;
    }
    const int count = static_cast<int>(options.size());
    index = std::clamp(index, 0, count - 1);
    const int old = index;
    const float arrow_w = std::min(r.h * 1.2f, r.w * 0.25f);
    const Rect left{r.x, r.y, arrow_w, r.h};
    const Rect right{r.right() - arrow_w, r.y, arrow_w, r.h};
    const Rect middle{r.x + arrow_w, r.y, r.w - 2 * arrow_w, r.h};

    tooltip_area(id, r, tooltip);
    if (button(id ^ 0x1111, left, "<", tooltip, enabled && index > 0)) {
        --index;
    }
    if (button(id ^ 0x2222, right, ">", tooltip, enabled && index < count - 1)) {
        ++index;
    }
    // Clicking the value moves to the next option, wrapping around.
    const Interaction it = interact(id ^ 0x3333, middle, enabled, tooltip);
    if (it.clicked) {
        index = (index + 1) % count;
    }
    draw_.rect(middle, it.hovered ? theme_.button_hover.with_alpha(0.6f) : theme_.button_active);
    label(middle.inset(s(6.0f)), options[static_cast<std::size_t>(index)], style(theme_.body),
          enabled ? theme_.text : theme_.text_disabled, Align::Center);
    return index != old;
}

Context::ScrollState& Context::scroll_state(Id id) {
    for (ScrollState& st : scrolls_) {
        if (st.id == id) {
            return st;
        }
    }
    scrolls_.push_back({id, 0.0f});
    return scrolls_.back();
}

float Context::begin_scroll(Id id, const Rect& viewport) {
    ScrollState& st = scroll_state(id);
    if (!blocked_ && input_.wheel != 0.0f && mouse_in(viewport)) {
        st.offset -= input_.wheel * s(60.0f);
        input_.wheel = 0.0f;  // Consumed by the innermost region.
    }
    st.offset = std::max(0.0f, st.offset);
    scroll_stack_.push_back({id, viewport});
    draw_.push_clip(viewport);
    return viewport.y - std::round(st.offset);
}

void Context::end_scroll(float content_height) {
    if (scroll_stack_.empty()) {
        return;
    }
    const ActiveScroll active = scroll_stack_.back();
    scroll_stack_.pop_back();
    draw_.pop_clip();
    ScrollState& st = scroll_state(active.id);
    const float max_offset = std::max(0.0f, content_height - active.viewport.h);
    st.offset = std::clamp(st.offset, 0.0f, max_offset);
    if (max_offset > 0.0f) {
        const Rect& v = active.viewport;
        const float bar_w = std::max(2.0f, std::round(s(5.0f)));
        const float thumb_h = std::max(s(24.0f), v.h * v.h / content_height);
        const float thumb_y = v.y + (v.h - thumb_h) * (st.offset / max_offset);
        draw_.rect({v.right() - bar_w, v.y, bar_w, v.h}, theme_.button_active.with_alpha(0.6f));
        draw_.rect({v.right() - bar_w, thumb_y, bar_w, thumb_h}, theme_.panel_border);
    }
}

void Context::end_frame() {
    // The held widget is released only after this frame's widgets have seen
    // the button go up, so they can report the click.
    if (!input_.mouse_down) {
        active_id_ = 0;
    }
    if (frame_tooltip_id_ != tooltip_id_) {
        tooltip_id_ = frame_tooltip_id_;
        tooltip_since_ns_ = now_ns_;
    }
    if (!tooltips_enabled_ || tooltip_id_ == 0 || now_ns_ - tooltip_since_ns_ < tooltip_delay_ns_ ||
        frame_tooltip_text_.empty()) {
        return;
    }
    const TextStyle st = style(theme_.small + 1);
    const float pad = s(8.0f);
    const float max_w = std::min(s(420.0f), width_ - 2 * pad);
    const auto lines = text_.wrap(st, frame_tooltip_text_, max_w - 2 * pad);
    float w = 0.0f;
    for (const std::string& line : lines) {
        w = std::max(w, text_.measure(st, line));
    }
    const float lh = text_.line_height(st);
    const float box_w = w + 2 * pad;
    const float box_h = static_cast<float>(lines.size()) * lh + 2 * pad;
    // Below the widget if it fits, otherwise above; kept on screen.
    float x = std::clamp(input_.mouse_x + s(12.0f), 0.0f, std::max(0.0f, width_ - box_w));
    float y = frame_tooltip_anchor_.bottom() + s(6.0f);
    if (y + box_h > height_) {
        y = frame_tooltip_anchor_.y - box_h - s(6.0f);
    }
    y = std::clamp(y, 0.0f, std::max(0.0f, height_ - box_h));
    const Rect box{std::round(x), std::round(y), std::round(box_w), std::round(box_h)};
    draw_.rect(box, theme_.tooltip);
    draw_.rect_outline(box, theme_.panel_border, std::max(1.0f, std::round(s(1.0f))));
    float ly = box.y + pad;
    for (const std::string& line : lines) {
        text_.draw(draw_, st, box.x + pad, ly, line, theme_.text);
        ly += lh;
    }
}

}  // namespace sc::ui
