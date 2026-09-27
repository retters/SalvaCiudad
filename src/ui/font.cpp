#include "ui/font.h"

#include <cmath>

#include <stb_truetype.h>

namespace sc::ui {

Font::Font() : info_(std::make_unique<stbtt_fontinfo>()) {}

Font::~Font() = default;

bool Font::load(std::vector<std::uint8_t> data) {
    loaded_ = false;
    glyph_cache_.clear();
    if (data.size() < 12 || data.size() > kMaxFileBytes) {
        return false;
    }
    data_ = std::move(data);
    if (stbtt_GetNumberOfFonts(data_.data()) < 1) {
        return false;
    }
    const int offset = stbtt_GetFontOffsetForIndex(data_.data(), 0);
    if (offset < 0 || static_cast<std::size_t>(offset) >= data_.size()) {
        return false;
    }
    if (stbtt_InitFont(info_.get(), data_.data(), offset) == 0) {
        return false;
    }
    stbtt_GetFontVMetrics(info_.get(), &ascent_, &descent_, &line_gap_);
    if (ascent_ <= 0 || ascent_ - descent_ <= 0) {
        return false;
    }
    loaded_ = true;
    return true;
}

float Font::scale(int px) const {
    return stbtt_ScaleForMappingEmToPixels(info_.get(), static_cast<float>(px));
}

float Font::ascent(int px) const {
    return std::ceil(static_cast<float>(ascent_) * scale(px));
}

float Font::descent(int px) const {
    return std::floor(static_cast<float>(descent_) * scale(px));
}

float Font::line_height(int px) const {
    return std::ceil(static_cast<float>(ascent_ - descent_ + line_gap_) * scale(px));
}

int Font::glyph_index(std::uint32_t codepoint) const {
    const auto it = glyph_cache_.find(codepoint);
    if (it != glyph_cache_.end()) {
        return it->second;
    }
    const int g = stbtt_FindGlyphIndex(info_.get(), static_cast<int>(codepoint));
    glyph_cache_.emplace(codepoint, g);
    return g;
}

float Font::advance(int px, int glyph) const {
    int adv = 0;
    int lsb = 0;
    stbtt_GetGlyphHMetrics(info_.get(), glyph, &adv, &lsb);
    return static_cast<float>(adv) * scale(px);
}

float Font::kerning(int px, int left_glyph, int right_glyph) const {
    return static_cast<float>(stbtt_GetGlyphKernAdvance(info_.get(), left_glyph, right_glyph)) * scale(px);
}

Font::Bitmap Font::rasterize(int px, int glyph) const {
    Bitmap bmp;
    const float s = scale(px);
    int x0 = 0;
    int y0 = 0;
    int x1 = 0;
    int y1 = 0;
    stbtt_GetGlyphBitmapBox(info_.get(), glyph, s, s, &x0, &y0, &x1, &y1);
    bmp.x0 = x0;
    bmp.y0 = y0;
    bmp.w = x1 - x0;
    bmp.h = y1 - y0;
    // Guard against absurd boxes from a damaged font.
    if (bmp.w <= 0 || bmp.h <= 0 || bmp.w > 4 * px + 64 || bmp.h > 4 * px + 64) {
        bmp.w = 0;
        bmp.h = 0;
        return bmp;
    }
    bmp.pixels.resize(static_cast<std::size_t>(bmp.w) * static_cast<std::size_t>(bmp.h));
    stbtt_MakeGlyphBitmap(info_.get(), bmp.pixels.data(), bmp.w, bmp.h, bmp.w, s, s, glyph);
    return bmp;
}

}  // namespace sc::ui
