#include "ui/text.h"

#include <algorithm>
#include <cmath>

#include "core/log.h"
#include "core/text.h"

namespace sc::ui {

namespace {

constexpr std::string_view kEllipsis = "\xE2\x80\xA6";  // U+2026

std::uint64_t cache_key(FontRole role, int px, int glyph) {
    return (static_cast<std::uint64_t>(role) << 56) | (static_cast<std::uint64_t>(px & 0xFFFF) << 32) |
           static_cast<std::uint32_t>(glyph);
}

// Glyph for a code point, using U+FFFD or '?' when the font lacks it.
int find_glyph(const Font& f, std::uint32_t cp) {
    int g = f.glyph_index(cp);
    if (g == 0 && cp != ' ') {
        g = f.glyph_index(0xFFFD);
        if (g == 0) {
            g = f.glyph_index('?');
        }
    }
    return g;
}

}  // namespace

void TextRenderer::set_font(FontRole role, const Font* font) {
    fonts_[static_cast<std::size_t>(role)] = font;
    cache_.clear();
}

const Font* TextRenderer::font(FontRole role) const {
    const Font* f = fonts_[static_cast<std::size_t>(role)];
    if (f == nullptr || !f->loaded()) {
        f = fonts_[static_cast<std::size_t>(FontRole::Regular)];
    }
    return (f != nullptr && f->loaded()) ? f : nullptr;
}

float TextRenderer::line_height(TextStyle style) const {
    const Font* f = font(style.role);
    return f != nullptr ? f->line_height(style.px) : static_cast<float>(style.px);
}

float TextRenderer::ascent(TextStyle style) const {
    const Font* f = font(style.role);
    return f != nullptr ? f->ascent(style.px) : static_cast<float>(style.px);
}

float TextRenderer::measure(TextStyle style, std::string_view text) const {
    const Font* f = font(style.role);
    if (f == nullptr) {
        return 0.0f;
    }
    float width = 0.0f;
    int prev = 0;
    std::size_t i = 0;
    while (i < text.size()) {
        const std::uint32_t cp = text::next_codepoint(text, i);
        if (cp == '\n') {
            break;
        }
        const int g = find_glyph(*f, cp);
        if (prev != 0) {
            width += f->kerning(style.px, prev, g);
        }
        width += f->advance(style.px, g);
        prev = g;
    }
    return std::ceil(width);
}

const TextRenderer::CachedGlyph* TextRenderer::glyph(TextStyle style, const Font& f, int glyph_index) {
    if (cache_generation_ != atlas_.generation()) {
        cache_.clear();
        cache_generation_ = atlas_.generation();
    }
    const std::uint64_t key = cache_key(style.role, style.px, glyph_index);
    if (const auto it = cache_.find(key); it != cache_.end()) {
        return &it->second;
    }
    const Font::Bitmap bmp = f.rasterize(style.px, glyph_index);
    CachedGlyph cached;
    if (bmp.w > 0 && bmp.h > 0) {
        AtlasRegion region;
        if (!atlas_.allocate(bmp.w, bmp.h, region)) {
            // Full: start over. Glyphs already placed this frame may show
            // wrong for one frame (decision D-206).
            log::warn("ui: glyph atlas full, clearing it");
            atlas_.clear();
            cache_.clear();
            cache_generation_ = atlas_.generation();
            if (!atlas_.allocate(bmp.w, bmp.h, region)) {
                return nullptr;
            }
        }
        atlas_.write(region, bmp.pixels.data(), bmp.w);
        const float inv = 1.0f / static_cast<float>(atlas_.size());
        cached = {static_cast<float>(region.x) * inv, static_cast<float>(region.y) * inv,
                  static_cast<float>(region.x + region.w) * inv, static_cast<float>(region.y + region.h) * inv,
                  bmp.x0, bmp.y0, bmp.w, bmp.h};
    }
    return &cache_.emplace(key, cached).first->second;
}

float TextRenderer::draw(DrawList& list, TextStyle style, float x, float y, std::string_view text, Color color) {
    const Font* f = font(style.role);
    if (f == nullptr) {
        return 0.0f;
    }
    const float baseline = std::round(y + f->ascent(style.px));
    float pen = x;
    int prev = 0;
    std::size_t i = 0;
    while (i < text.size()) {
        const std::uint32_t cp = text::next_codepoint(text, i);
        if (cp == '\n') {
            break;
        }
        const int g = find_glyph(*f, cp);
        if (prev != 0) {
            pen += f->kerning(style.px, prev, g);
        }
        if (const CachedGlyph* cg = glyph(style, *f, g); cg != nullptr && cg->w > 0) {
            const Rect r{std::round(pen) + static_cast<float>(cg->x0), baseline + static_cast<float>(cg->y0),
                         static_cast<float>(cg->w), static_cast<float>(cg->h)};
            list.image(r, cg->u0, cg->v0, cg->u1, cg->v1, color);
        }
        pen += f->advance(style.px, g);
        prev = g;
    }
    return std::ceil(pen - x);
}

namespace {

Color lerp_color(Color a, Color b, float t) {
    const auto mix = [t](std::uint8_t p, std::uint8_t q) {
        return static_cast<std::uint8_t>(static_cast<float>(p) + (static_cast<float>(q) - static_cast<float>(p)) * t + 0.5f);
    };
    return {mix(a.r, b.r), mix(a.g, b.g), mix(a.b, b.b), mix(a.a, b.a)};
}

// The gradient's color at `t` in [0, 1].
Color gradient_at(const std::vector<TextRenderer::GradientStop>& stops, float t) {
    if (t <= stops.front().at) {
        return stops.front().color;
    }
    for (std::size_t i = 1; i < stops.size(); ++i) {
        if (t <= stops[i].at) {
            const float span = stops[i].at - stops[i - 1].at;
            return lerp_color(stops[i - 1].color, stops[i].color, span > 0.0f ? (t - stops[i - 1].at) / span : 1.0f);
        }
    }
    return stops.back().color;
}

}  // namespace

float TextRenderer::draw_gradient(DrawList& list, TextStyle style, float x, float y, std::string_view text,
                                  const std::vector<GradientStop>& stops, float band_top, float band_height) {
    const Font* f = font(style.role);
    if (f == nullptr || stops.size() < 2 || band_height <= 0.0f) {
        return 0.0f;
    }
    const float baseline = std::round(y + f->ascent(style.px));
    float pen = x;
    int prev = 0;
    std::size_t i = 0;
    while (i < text.size()) {
        const std::uint32_t cp = text::next_codepoint(text, i);
        if (cp == '\n') {
            break;
        }
        const int g = find_glyph(*f, cp);
        if (prev != 0) {
            pen += f->kerning(style.px, prev, g);
        }
        if (const CachedGlyph* cg = glyph(style, *f, g); cg != nullptr && cg->w > 0) {
            const float gx = std::round(pen) + static_cast<float>(cg->x0);
            const float gy = baseline + static_cast<float>(cg->y0);
            const float gh = static_cast<float>(cg->h);
            // Cut the glyph at every stop so each slice blends between two stop colors.
            std::vector<float> cuts{0.0f, gh};
            for (const GradientStop& s : stops) {
                const float cut = s.at * band_height + band_top - gy;
                if (cut > 0.0f && cut < gh) {
                    cuts.push_back(cut);
                }
            }
            std::sort(cuts.begin(), cuts.end());
            for (std::size_t k = 1; k < cuts.size(); ++k) {
                if (cuts[k] - cuts[k - 1] < 0.01f) {
                    continue;
                }
                const float t0 = (gy + cuts[k - 1] - band_top) / band_height;
                const float t1 = (gy + cuts[k] - band_top) / band_height;
                const float v0 = cg->v0 + (cg->v1 - cg->v0) * (cuts[k - 1] / gh);
                const float v1 = cg->v0 + (cg->v1 - cg->v0) * (cuts[k] / gh);
                list.image_vgradient({gx, gy + cuts[k - 1], static_cast<float>(cg->w), cuts[k] - cuts[k - 1]}, cg->u0, v0,
                                     cg->u1, v1, gradient_at(stops, t0), gradient_at(stops, t1));
            }
        }
        pen += f->advance(style.px, g);
        prev = g;
    }
    return std::ceil(pen - x);
}

float TextRenderer::rasterize(TextStyle style, float x, float y, std::string_view text, AlphaMask& into) const {
    const Font* f = font(style.role);
    if (f == nullptr) {
        return 0.0f;
    }
    // The same pen and rounding as draw(), so the mask lines up with the drawn glyphs.
    const float baseline = std::round(y + f->ascent(style.px));
    float pen = x;
    int prev = 0;
    std::size_t i = 0;
    while (i < text.size()) {
        const std::uint32_t cp = text::next_codepoint(text, i);
        if (cp == '\n') {
            break;
        }
        const int g = find_glyph(*f, cp);
        if (prev != 0) {
            pen += f->kerning(style.px, prev, g);
        }
        const Font::Bitmap bmp = f->rasterize(style.px, g);
        const int gx = static_cast<int>(std::round(pen)) + bmp.x0;
        const int gy = static_cast<int>(baseline) + bmp.y0;
        for (int row = 0; row < bmp.h; ++row) {
            for (int col = 0; col < bmp.w; ++col) {
                const std::uint8_t c = bmp.pixels[static_cast<std::size_t>(row * bmp.w + col)];
                if (c != 0) {
                    into.stamp_max(gx + col, gy + row, static_cast<float>(c) / 255.0f);
                }
            }
        }
        pen += f->advance(style.px, g);
        prev = g;
    }
    return std::ceil(pen - x);
}

std::vector<std::string> TextRenderer::wrap(TextStyle style, std::string_view text, float max_width) const {
    std::vector<std::string> lines;
    std::size_t para_start = 0;
    while (para_start <= text.size()) {
        const std::size_t nl = text.find('\n', para_start);
        const std::string_view para =
            text.substr(para_start, nl == std::string_view::npos ? std::string_view::npos : nl - para_start);
        std::string line;
        std::size_t i = 0;
        while (i < para.size()) {
            // Next word, including its trailing spaces.
            std::size_t end = para.find(' ', i);
            end = end == std::string_view::npos ? para.size() : para.find_first_not_of(' ', end);
            end = end == std::string_view::npos ? para.size() : end;
            const std::string_view word = para.substr(i, end - i);
            std::string candidate = line + std::string(word);
            // Trailing spaces never force a break.
            std::string_view trimmed = candidate;
            while (!trimmed.empty() && trimmed.back() == ' ') {
                trimmed.remove_suffix(1);
            }
            if (measure(style, trimmed) <= max_width || line.empty()) {
                if (line.empty() && measure(style, trimmed) > max_width) {
                    // A word wider than the line: break it by characters.
                    std::size_t k = 0;
                    std::string piece;
                    while (k < word.size()) {
                        std::size_t next = k;
                        (void)text::next_codepoint(word, next);
                        const std::string grown = piece + std::string(word.substr(k, next - k));
                        if (!piece.empty() && measure(style, grown) > max_width) {
                            lines.push_back(piece);
                            piece.clear();
                            continue;
                        }
                        piece = grown;
                        k = next;
                    }
                    line = piece;
                } else {
                    line = std::move(candidate);
                }
                i = end;
            } else {
                while (!line.empty() && line.back() == ' ') {
                    line.pop_back();
                }
                lines.push_back(line);
                line.clear();
            }
        }
        while (!line.empty() && line.back() == ' ') {
            line.pop_back();
        }
        lines.push_back(line);
        if (nl == std::string_view::npos) {
            break;
        }
        para_start = nl + 1;
    }
    return lines;
}

std::string TextRenderer::ellipsize(TextStyle style, std::string_view text, float max_width) const {
    if (measure(style, text) <= max_width) {
        return std::string(text);
    }
    const float ellipsis_w = measure(style, kEllipsis);
    std::string out;
    std::size_t i = 0;
    while (i < text.size()) {
        std::size_t next = i;
        (void)text::next_codepoint(text, next);
        const std::string grown = out + std::string(text.substr(i, next - i));
        if (measure(style, grown) + ellipsis_w > max_width) {
            break;
        }
        out = grown;
        i = next;
    }
    while (!out.empty() && out.back() == ' ') {
        out.pop_back();
    }
    return out + std::string(kEllipsis);
}

}  // namespace sc::ui
