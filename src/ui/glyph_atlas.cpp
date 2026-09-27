#include "ui/glyph_atlas.h"

#include <algorithm>
#include <cstring>

namespace sc::ui {

GlyphAtlas::GlyphAtlas(int size) : size_(size), pixels_(static_cast<std::size_t>(size) * static_cast<std::size_t>(size)) {
    // Sample the middle of the white block so filtering never reaches the
    // empty border.
    white_uv_ = (static_cast<float>(kWhiteSize) * 0.5f) / static_cast<float>(size_);
    clear();
    generation_ = 0;
}

void GlyphAtlas::clear() {
    std::fill(pixels_.begin(), pixels_.end(), std::uint8_t{0});
    for (int y = 0; y < kWhiteSize; ++y) {
        std::memset(&pixels_[static_cast<std::size_t>(y) * static_cast<std::size_t>(size_)], 0xFF,
                    static_cast<std::size_t>(kWhiteSize));
    }
    shelf_x_ = kWhiteSize + kPadding;
    shelf_y_ = 0;
    shelf_h_ = kWhiteSize;
    ++generation_;
    mark_dirty({0, 0, size_, size_});
}

bool GlyphAtlas::allocate(int w, int h, AtlasRegion& out) {
    if (w <= 0 || h <= 0 || w + kPadding > size_ || h + kPadding > size_) {
        return false;
    }
    if (shelf_x_ + w + kPadding > size_) {
        // Start a new shelf below the current one.
        shelf_y_ += shelf_h_ + kPadding;
        shelf_x_ = 0;
        shelf_h_ = 0;
    }
    if (shelf_y_ + h + kPadding > size_) {
        return false;
    }
    out = {shelf_x_, shelf_y_, w, h};
    shelf_x_ += w + kPadding;
    shelf_h_ = std::max(shelf_h_, h);
    return true;
}

void GlyphAtlas::write(const AtlasRegion& region, const std::uint8_t* pixels, int pitch) {
    for (int row = 0; row < region.h; ++row) {
        std::memcpy(&pixels_[static_cast<std::size_t>(region.y + row) * static_cast<std::size_t>(size_) +
                             static_cast<std::size_t>(region.x)],
                    pixels + static_cast<std::ptrdiff_t>(row) * pitch, static_cast<std::size_t>(region.w));
    }
    mark_dirty(region);
}

void GlyphAtlas::mark_dirty(const AtlasRegion& r) {
    if (!has_dirty_) {
        dirty_ = r;
        has_dirty_ = true;
        return;
    }
    const int x0 = std::min(dirty_.x, r.x);
    const int y0 = std::min(dirty_.y, r.y);
    const int x1 = std::max(dirty_.x + dirty_.w, r.x + r.w);
    const int y1 = std::max(dirty_.y + dirty_.h, r.y + r.h);
    dirty_ = {x0, y0, x1 - x0, y1 - y0};
}

AtlasRegion GlyphAtlas::take_dirty() {
    const AtlasRegion r = has_dirty_ ? dirty_ : AtlasRegion{};
    has_dirty_ = false;
    return r;
}

}  // namespace sc::ui
