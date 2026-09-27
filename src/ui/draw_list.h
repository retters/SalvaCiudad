// CPU-side list of 2D triangles for the interface, grouped by clip rectangle.
// The renderer uploads and draws it; tests can inspect it without a GPU.
#pragma once

#include <cstdint>
#include <vector>

namespace sc::ui {

struct Rect {
    float x = 0.0f;
    float y = 0.0f;
    float w = 0.0f;
    float h = 0.0f;

    [[nodiscard]] float right() const { return x + w; }
    [[nodiscard]] float bottom() const { return y + h; }
    [[nodiscard]] bool contains(float px, float py) const { return px >= x && px < x + w && py >= y && py < y + h; }
    [[nodiscard]] Rect inset(float d) const { return {x + d, y + d, w - 2 * d, h - 2 * d}; }
    [[nodiscard]] Rect intersect(const Rect& o) const;
    bool operator==(const Rect&) const = default;
};

// Straight (not premultiplied) RGBA. Color::rgb(0xRRGGBB) for literals.
struct Color {
    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;
    std::uint8_t a = 255;

    [[nodiscard]] static constexpr Color rgb(std::uint32_t rgb, std::uint8_t alpha = 255) {
        return {static_cast<std::uint8_t>(rgb >> 16), static_cast<std::uint8_t>(rgb >> 8),
                static_cast<std::uint8_t>(rgb), alpha};
    }
    [[nodiscard]] Color with_alpha(float factor) const;
};

struct Vertex {
    float x, y;
    float u, v;
    std::uint8_t r, g, b, a;
};

struct DrawCommand {
    std::uint32_t first_index = 0;
    std::uint32_t index_count = 0;
    Rect clip;
};

class DrawList {
public:
    void reset(float width, float height, float white_u, float white_v);

    void push_clip(const Rect& r);  // Intersected with the current clip.
    void pop_clip();
    [[nodiscard]] const Rect& clip() const { return clip_stack_.back(); }

    void rect(const Rect& r, Color c);
    void rect_outline(const Rect& r, Color c, float thickness);
    // A textured quad; uv are atlas coordinates in [0, 1].
    void image(const Rect& r, float u0, float v0, float u1, float v1, Color c);

    [[nodiscard]] const std::vector<Vertex>& vertices() const { return vertices_; }
    [[nodiscard]] const std::vector<std::uint32_t>& indices() const { return indices_; }
    [[nodiscard]] const std::vector<DrawCommand>& commands() const { return commands_; }
    [[nodiscard]] float width() const { return width_; }
    [[nodiscard]] float height() const { return height_; }

private:
    void quad(const Rect& r, float u0, float v0, float u1, float v1, Color c);
    void start_command();

    std::vector<Vertex> vertices_;
    std::vector<std::uint32_t> indices_;
    std::vector<DrawCommand> commands_;
    std::vector<Rect> clip_stack_;
    float width_ = 0.0f;
    float height_ = 0.0f;
    float white_u_ = 0.0f;
    float white_v_ = 0.0f;
};

}  // namespace sc::ui
