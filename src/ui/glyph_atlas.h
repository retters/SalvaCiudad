// Single-channel texture atlas for glyphs, packed in shelves. A small white
// block at the origin serves solid shapes. The renderer uploads the dirty
// region each frame.
#pragma once

#include <cstdint>
#include <vector>

namespace sc::ui {

struct AtlasRegion {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
};

class GlyphAtlas {
public:
    static constexpr int kWhiteSize = 4;
    static constexpr int kPadding = 1;

    explicit GlyphAtlas(int size = 2048);

    // Reserves a w x h area. Returns false if the atlas is full; the caller
    // then calls clear() and requests its glyphs again.
    bool allocate(int w, int h, AtlasRegion& out);

    // Copies `pixels` (w x h, one byte per pixel) into the region.
    void write(const AtlasRegion& region, const std::uint8_t* pixels, int pitch);

    // Forgets every glyph, keeping the white block.
    void clear();

    [[nodiscard]] int size() const { return size_; }
    [[nodiscard]] const std::uint8_t* pixels() const { return pixels_.data(); }
    [[nodiscard]] float white_u() const { return white_uv_; }
    [[nodiscard]] float white_v() const { return white_uv_; }
    // Increments on clear(); cached glyph positions from before are stale.
    [[nodiscard]] std::uint32_t generation() const { return generation_; }

    // Area changed since the last take_dirty(); empty if nothing changed.
    [[nodiscard]] AtlasRegion take_dirty();

private:
    void mark_dirty(const AtlasRegion& r);

    int size_;
    std::vector<std::uint8_t> pixels_;
    int shelf_x_ = 0;
    int shelf_y_ = 0;
    int shelf_h_ = 0;
    float white_uv_ = 0.0f;
    std::uint32_t generation_ = 0;
    AtlasRegion dirty_{};
    bool has_dirty_ = false;
};

}  // namespace sc::ui
