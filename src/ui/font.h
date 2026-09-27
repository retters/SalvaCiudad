// A TrueType font loaded in memory, with metrics in pixels. stb_truetype is
// not hardened against malicious files, so fonts are only loaded from the
// game's own data folder (decision D-205).
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <unordered_map>
#include <vector>

struct stbtt_fontinfo;

namespace sc::ui {

class Font {
public:
    static constexpr std::size_t kMaxFileBytes = 16u * 1024u * 1024u;

    Font();
    ~Font();
    Font(const Font&) = delete;
    Font& operator=(const Font&) = delete;

    bool load(std::vector<std::uint8_t> data);
    [[nodiscard]] bool loaded() const { return loaded_; }

    // Scale for a font size in pixels per em, like CSS font-size.
    [[nodiscard]] float scale(int px) const;
    [[nodiscard]] float ascent(int px) const;
    [[nodiscard]] float descent(int px) const;  // Negative.
    [[nodiscard]] float line_height(int px) const;

    // 0 if the font has no glyph for the code point.
    [[nodiscard]] int glyph_index(std::uint32_t codepoint) const;
    [[nodiscard]] float advance(int px, int glyph) const;
    [[nodiscard]] float kerning(int px, int left_glyph, int right_glyph) const;

    // Rasterizes a glyph. `x0`, `y0` are offsets from the pen position on the
    // baseline. Empty `pixels` for blank glyphs such as the space.
    struct Bitmap {
        std::vector<std::uint8_t> pixels;
        int w = 0;
        int h = 0;
        int x0 = 0;
        int y0 = 0;
    };
    [[nodiscard]] Bitmap rasterize(int px, int glyph) const;

private:
    std::vector<std::uint8_t> data_;
    std::unique_ptr<stbtt_fontinfo> info_;
    bool loaded_ = false;
    int ascent_ = 0;
    int descent_ = 0;
    int line_gap_ = 0;
    mutable std::unordered_map<std::uint32_t, int> glyph_cache_;
};

}  // namespace sc::ui
