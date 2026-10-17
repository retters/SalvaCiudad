#include "ui/rml/rml_font_engine.h"

#include <algorithm>
#include <cctype>
#include <cmath>

#include <RmlUi/Core/RenderManager.h>
#include <RmlUi/Core/StringUtilities.h>

namespace sc::rml {

namespace {

std::string lower(std::string_view s) {
    std::string out(s);
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return out;
}

constexpr std::uint32_t kEllipsis = 0x2026;

}  // namespace

FontEngine::FontEngine(ui::GlyphAtlas& atlas, const ui::FontLibrary& fonts)
    : atlas_(atlas), fonts_(fonts), atlas_texture_(make_atlas_texture()) {}

Rml::CallbackTextureSource FontEngine::make_atlas_texture() {
    return Rml::CallbackTextureSource([this](const Rml::CallbackTextureInterface& texture) {
        texture.SetTextureHandle(kAtlasTexture, Rml::Vector2i(atlas_.size(), atlas_.size()));
        return true;
    });
}

void FontEngine::Shutdown() {
    ReleaseFontResources();
    atlas_texture_ = make_atlas_texture();
}

void FontEngine::set_ui_family(std::string_view id) {
    if (ui_family_ != id) {
        ui_family_ = std::string(id);
        ++family_changes_;
    }
}

bool FontEngine::LoadFontFace(const Rml::String&, int, bool, Rml::Style::FontWeight) {
    return true;  // Fonts come from data/fonts only.
}

bool FontEngine::LoadFontFace(const Rml::String&, int, const Rml::String&, Rml::Style::FontStyle,
                              Rml::Style::FontWeight, bool) {
    return true;
}

bool FontEngine::LoadFontFace(Rml::Span<const Rml::byte>, int, const Rml::String&, Rml::Style::FontStyle,
                              Rml::Style::FontWeight, bool) {
    // The debugger's embedded font: its family resolves to the interface's.
    return true;
}

const ui::Font* FontEngine::resolve(std::string_view family, bool bold) const {
    const std::string name = lower(family);
    if (name == "logo") {
        return fonts_.logo();
    }
    if (name == "logo-small") {
        return fonts_.logo_small();
    }
    const ui::FontFamily* chosen = fonts_.ui_family(ui_family_);
    for (const ui::FontFamily& f : fonts_.ui_families()) {
        if (lower(f.name) == name || f.id == name) {
            chosen = &f;
        }
    }
    if (chosen == nullptr) {
        return nullptr;
    }
    if (bold && chosen->bold != nullptr) {
        return chosen->bold.get();
    }
    return chosen->regular.get();
}

Rml::FontFaceHandle FontEngine::GetFontFaceHandle(const Rml::String& family, Rml::Style::FontStyle,
                                                  Rml::Style::FontWeight weight, int size) {
    const bool bold = static_cast<int>(weight) >= 600;
    const ui::Font* font = resolve(family, bold);
    if (font == nullptr || !font->loaded() || size < 1 || size > 512) {
        return 0;
    }
    const auto key = std::make_pair(font, size);
    if (const auto it = face_index_.find(key); it != face_index_.end()) {
        return it->second;
    }
    Face f;
    f.font = font;
    f.px = size;
    f.metrics.size = size;
    f.metrics.ascent = font->ascent(size);
    f.metrics.descent = -font->descent(size);
    f.metrics.line_spacing = font->line_height(size);
    const ui::Font::Bitmap x = font->rasterize(size, font->glyph_index('x'));
    f.metrics.x_height = x.h > 0 ? static_cast<float>(-x.y0) : static_cast<float>(size) * 0.5f;
    f.metrics.underline_position = std::max(1.0f, static_cast<float>(size) * 0.1f);
    f.metrics.underline_thickness = std::max(1.0f, std::round(static_cast<float>(size) / 14.0f));
    f.metrics.has_ellipsis = font->glyph_index(kEllipsis) != 0;
    faces_.push_back(f);
    const auto handle = static_cast<Rml::FontFaceHandle>(faces_.size());
    face_index_.emplace(key, handle);
    return handle;
}

Rml::FontEffectsHandle FontEngine::PrepareFontEffects(Rml::FontFaceHandle, const Rml::FontEffectList&) {
    return 0;  // No font effects yet (shadows and glows come with the styles).
}

const FontEngine::Face* FontEngine::face(Rml::FontFaceHandle handle) const {
    if (handle == 0 || handle > faces_.size()) {
        return nullptr;
    }
    return &faces_[handle - 1];
}

const Rml::FontMetrics& FontEngine::GetFontMetrics(Rml::FontFaceHandle handle) {
    const Face* f = face(handle);
    return f != nullptr ? f->metrics : no_metrics_;
}

int FontEngine::GetStringWidth(Rml::FontFaceHandle handle, Rml::StringView string,
                               const Rml::TextShapingContext& text_shaping_context, Rml::Character prior_character) {
    const Face* f = face(handle);
    if (f == nullptr) {
        return 0;
    }
    float width = 0.0f;
    int previous = prior_character != Rml::Character::Null ? f->font->glyph_index(static_cast<std::uint32_t>(prior_character)) : 0;
    for (auto it = Rml::StringIteratorU8(string); it; ++it) {
        const int g = f->font->glyph_index(static_cast<std::uint32_t>(*it));
        if (previous != 0) {
            width += f->font->kerning(f->px, previous, g);
        }
        width += f->font->advance(f->px, g) + text_shaping_context.letter_spacing;
        previous = g;
    }
    return static_cast<int>(std::ceil(width));
}

const FontEngine::Glyph* FontEngine::glyph(Rml::FontFaceHandle handle, const Face& f, int glyph_index) {
    if (glyphs_generation_ != atlas_.generation()) {
        glyphs_.clear();  // Somebody cleared the shared atlas.
        glyphs_generation_ = atlas_.generation();
    }
    const std::uint64_t key = (static_cast<std::uint64_t>(handle) << 32) | static_cast<std::uint32_t>(glyph_index);
    if (const auto it = glyphs_.find(key); it != glyphs_.end()) {
        return &it->second;
    }
    const ui::Font::Bitmap bitmap = f.font->rasterize(f.px, glyph_index);
    Glyph g;
    g.x0 = bitmap.x0;
    g.y0 = bitmap.y0;
    g.w = bitmap.w;
    g.h = bitmap.h;
    if (bitmap.w > 0 && bitmap.h > 0) {
        ui::AtlasRegion region;
        if (!atlas_.allocate(bitmap.w, bitmap.h, region)) {
            atlas_.clear();
            glyphs_.clear();
            glyphs_generation_ = atlas_.generation();
            if (!atlas_.allocate(bitmap.w, bitmap.h, region)) {
                return nullptr;
            }
        }
        atlas_.write(region, bitmap.pixels.data(), bitmap.w);
        const auto size = static_cast<float>(atlas_.size());
        g.u0 = static_cast<float>(region.x) / size;
        g.v0 = static_cast<float>(region.y) / size;
        g.u1 = static_cast<float>(region.x + region.w) / size;
        g.v1 = static_cast<float>(region.y + region.h) / size;
    }
    return &glyphs_.emplace(key, g).first->second;
}

int FontEngine::GenerateString(Rml::RenderManager& render_manager, Rml::FontFaceHandle face_handle,
                               Rml::FontEffectsHandle, Rml::StringView string, Rml::Vector2f position,
                               Rml::ColourbPremultiplied colour, float,
                               const Rml::TextShapingContext& text_shaping_context, Rml::TexturedMeshList& mesh_list) {
    const Face* f = face(face_handle);
    if (f == nullptr) {
        return 0;
    }
    Rml::Mesh mesh;
    float pen = position.x;
    const float baseline = std::round(position.y);
    int previous = 0;
    for (auto it = Rml::StringIteratorU8(string); it; ++it) {
        const int index = f->font->glyph_index(static_cast<std::uint32_t>(*it));
        if (previous != 0) {
            pen += f->font->kerning(f->px, previous, index);
        }
        previous = index;
        const Glyph* g = glyph(face_handle, *f, index);
        if (g != nullptr && g->w > 0 && g->h > 0) {
            const float x0 = std::round(pen) + static_cast<float>(g->x0);
            const float y0 = baseline + static_cast<float>(g->y0);
            const float x1 = x0 + static_cast<float>(g->w);
            const float y1 = y0 + static_cast<float>(g->h);
            const auto base = static_cast<int>(mesh.vertices.size());
            mesh.vertices.push_back({{x0, y0}, colour, {g->u0, g->v0}});
            mesh.vertices.push_back({{x1, y0}, colour, {g->u1, g->v0}});
            mesh.vertices.push_back({{x1, y1}, colour, {g->u1, g->v1}});
            mesh.vertices.push_back({{x0, y1}, colour, {g->u0, g->v1}});
            for (const int i : {0, 1, 2, 0, 2, 3}) {
                mesh.indices.push_back(base + i);
            }
        }
        pen += f->font->advance(f->px, index) + text_shaping_context.letter_spacing;
    }
    if (mesh) {
        mesh_list.push_back({std::move(mesh), atlas_texture_.GetTexture(render_manager)});
    }
    return static_cast<int>(std::ceil(pen - position.x));
}

int FontEngine::GetVersion(Rml::FontFaceHandle) {
    // New text geometry whenever the atlas was cleared (glyph places changed).
    return static_cast<int>(atlas_.generation()) + family_changes_ * 1000003;
}

void FontEngine::ReleaseFontResources() {
    faces_.clear();
    face_index_.clear();
    glyphs_.clear();
}

}  // namespace sc::rml
