// Measures, wraps and draws text with the fonts of the interface. Glyphs are
// rasterized on demand into the shared atlas.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "ui/draw_list.h"
#include "ui/font.h"
#include "ui/glyph_atlas.h"

namespace sc::ui {

enum class FontRole : std::uint8_t { Regular, Bold, Logo, Count };

struct TextStyle {
    FontRole role = FontRole::Regular;
    int px = 18;  // Final pixel size, already scaled.
};

class TextRenderer {
public:
    explicit TextRenderer(GlyphAtlas& atlas) : atlas_(atlas) {}

    // Fonts are owned elsewhere. A missing role falls back to Regular.
    void set_font(FontRole role, const Font* font);

    [[nodiscard]] float measure(TextStyle style, std::string_view text) const;
    [[nodiscard]] float line_height(TextStyle style) const;
    [[nodiscard]] float ascent(TextStyle style) const;

    // Draws one line with its top-left corner at (x, y). Returns the width.
    float draw(DrawList& list, TextStyle style, float x, float y, std::string_view text, Color color);

    // Splits at line breaks and between words so each line fits `max_width`.
    // A single word longer than the width is split between characters.
    [[nodiscard]] std::vector<std::string> wrap(TextStyle style, std::string_view text, float max_width) const;

    // The text, or its beginning followed by "…" so that it fits.
    [[nodiscard]] std::string ellipsize(TextStyle style, std::string_view text, float max_width) const;

private:
    struct CachedGlyph {
        float u0 = 0, v0 = 0, u1 = 0, v1 = 0;
        int x0 = 0, y0 = 0, w = 0, h = 0;
    };

    [[nodiscard]] const Font* font(FontRole role) const;
    const CachedGlyph* glyph(TextStyle style, const Font& f, int glyph_index);

    GlyphAtlas& atlas_;
    std::array<const Font*, static_cast<std::size_t>(FontRole::Count)> fonts_{};
    std::unordered_map<std::uint64_t, CachedGlyph> cache_;
    std::uint32_t cache_generation_ = 0;
};

}  // namespace sc::ui
