#include "ui/draw_list.h"

#include <algorithm>

namespace sc::ui {

Rect Rect::intersect(const Rect& o) const {
    const float x0 = std::max(x, o.x);
    const float y0 = std::max(y, o.y);
    const float x1 = std::min(right(), o.right());
    const float y1 = std::min(bottom(), o.bottom());
    return {x0, y0, std::max(0.0f, x1 - x0), std::max(0.0f, y1 - y0)};
}

Color Color::with_alpha(float factor) const {
    const float a_scaled = std::clamp(static_cast<float>(a) * factor, 0.0f, 255.0f);
    return {r, g, b, static_cast<std::uint8_t>(a_scaled + 0.5f)};
}

void DrawList::reset(float width, float height, float white_u, float white_v) {
    vertices_.clear();
    indices_.clear();
    commands_.clear();
    clip_stack_.clear();
    width_ = width;
    height_ = height;
    white_u_ = white_u;
    white_v_ = white_v;
    clip_stack_.push_back({0.0f, 0.0f, width, height});
    start_command();
}

void DrawList::start_command() {
    DrawCommand cmd;
    cmd.first_index = static_cast<std::uint32_t>(indices_.size());
    cmd.clip = clip_stack_.back();
    // Reuse the last command if it has no triangles yet.
    if (!commands_.empty() && commands_.back().index_count == 0) {
        commands_.back() = cmd;
    } else {
        commands_.push_back(cmd);
    }
}

void DrawList::push_clip(const Rect& r) {
    clip_stack_.push_back(r.intersect(clip_stack_.back()));
    start_command();
}

void DrawList::pop_clip() {
    if (clip_stack_.size() > 1) {
        clip_stack_.pop_back();
        start_command();
    }
}

void DrawList::quad(const Rect& r, float u0, float v0, float u1, float v1, Color c) {
    if (r.w <= 0.0f || r.h <= 0.0f || c.a == 0) {
        return;
    }
    // Skip what the clip rectangle hides completely.
    const Rect& clip = clip_stack_.back();
    if (r.right() <= clip.x || r.x >= clip.right() || r.bottom() <= clip.y || r.y >= clip.bottom()) {
        return;
    }
    const auto base = static_cast<std::uint32_t>(vertices_.size());
    vertices_.push_back({r.x, r.y, u0, v0, c.r, c.g, c.b, c.a});
    vertices_.push_back({r.right(), r.y, u1, v0, c.r, c.g, c.b, c.a});
    vertices_.push_back({r.right(), r.bottom(), u1, v1, c.r, c.g, c.b, c.a});
    vertices_.push_back({r.x, r.bottom(), u0, v1, c.r, c.g, c.b, c.a});
    for (const std::uint32_t i : {0u, 1u, 2u, 0u, 2u, 3u}) {
        indices_.push_back(base + i);
    }
    commands_.back().index_count += 6;
}

void DrawList::rect(const Rect& r, Color c) {
    quad(r, white_u_, white_v_, white_u_, white_v_, c);
}

void DrawList::rect_outline(const Rect& r, Color c, float t) {
    rect({r.x, r.y, r.w, t}, c);
    rect({r.x, r.bottom() - t, r.w, t}, c);
    rect({r.x, r.y + t, t, r.h - 2 * t}, c);
    rect({r.right() - t, r.y + t, t, r.h - 2 * t}, c);
}

void DrawList::image(const Rect& r, float u0, float v0, float u1, float v1, Color c) {
    quad(r, u0, v0, u1, v1, c);
}

}  // namespace sc::ui
