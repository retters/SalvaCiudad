// RmlUi's font engine, built on the game's own fonts and glyph atlas instead
// of FreeType (phase 117, D-11703). Families a document can ask for:
//   "ui"          the interface family chosen in the settings (and any
//                 unknown family, so text always shows);
//   its name      every interface family of data/fonts/fonts.json by its
//                 display name, for example "Alegreya Sans";
//   "logo"        the font of the game's name;
//   "logo-small"  the font of the small line above it.
// A weight of 600 or more takes the family's bold face when it has one.
// Font files are never loaded from documents: data/fonts is the only source
// (D-205), so LoadFontFace only accepts and ignores the requests.
#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include <RmlUi/Core/CallbackTexture.h>
#include <RmlUi/Core/FontEngineInterface.h>

#include "ui/font.h"
#include "ui/font_library.h"
#include "ui/glyph_atlas.h"

namespace sc::rml {

class FontEngine final : public Rml::FontEngineInterface {
public:
    // The texture handle RmlUi receives for the glyph atlas; the renderer
    // knows it means the game's atlas and that its red channel is coverage.
    static constexpr Rml::TextureHandle kAtlasTexture = 1;

    FontEngine(ui::GlyphAtlas& atlas, const ui::FontLibrary& fonts);

    // The interface family ("ui"), by its id in fonts.json.
    void set_ui_family(std::string_view id);

    bool LoadFontFace(const Rml::String& file_name, int face_index, bool fallback_face,
                      Rml::Style::FontWeight weight) override;
    bool LoadFontFace(const Rml::String& file_name, int face_index, const Rml::String& family,
                      Rml::Style::FontStyle style, Rml::Style::FontWeight weight, bool fallback_face) override;
    bool LoadFontFace(Rml::Span<const Rml::byte> data, int face_index, const Rml::String& family,
                      Rml::Style::FontStyle style, Rml::Style::FontWeight weight, bool fallback_face) override;
    Rml::FontFaceHandle GetFontFaceHandle(const Rml::String& family, Rml::Style::FontStyle style,
                                          Rml::Style::FontWeight weight, int size) override;
    Rml::FontEffectsHandle PrepareFontEffects(Rml::FontFaceHandle handle,
                                              const Rml::FontEffectList& font_effects) override;
    const Rml::FontMetrics& GetFontMetrics(Rml::FontFaceHandle handle) override;
    int GetStringWidth(Rml::FontFaceHandle handle, Rml::StringView string,
                       const Rml::TextShapingContext& text_shaping_context,
                       Rml::Character prior_character) override;
    int GenerateString(Rml::RenderManager& render_manager, Rml::FontFaceHandle face_handle,
                       Rml::FontEffectsHandle font_effects_handle, Rml::StringView string, Rml::Vector2f position,
                       Rml::ColourbPremultiplied colour, float opacity,
                       const Rml::TextShapingContext& text_shaping_context, Rml::TexturedMeshList& mesh_list) override;
    int GetVersion(Rml::FontFaceHandle handle) override;
    void ReleaseFontResources() override;
    // RmlUi calls it before destroying its render managers: the atlas
    // texture they made for this engine must go first.
    void Shutdown() override;

private:
    struct Face {
        const ui::Font* font = nullptr;
        int px = 0;
        Rml::FontMetrics metrics{};
    };
    struct Glyph {
        float u0 = 0, v0 = 0, u1 = 0, v1 = 0;
        int x0 = 0, y0 = 0, w = 0, h = 0;
    };

    [[nodiscard]] const ui::Font* resolve(std::string_view family, bool bold) const;
    [[nodiscard]] Rml::CallbackTextureSource make_atlas_texture();
    [[nodiscard]] const Face* face(Rml::FontFaceHandle handle) const;
    // The glyph's place in the atlas, rasterizing it the first time; null if
    // the atlas is full even after clearing it.
    const Glyph* glyph(Rml::FontFaceHandle handle, const Face& f, int glyph_index);

    ui::GlyphAtlas& atlas_;
    const ui::FontLibrary& fonts_;
    std::string ui_family_;
    std::vector<Face> faces_;  // Handle = index + 1.
    std::map<std::pair<const ui::Font*, int>, Rml::FontFaceHandle> face_index_;
    std::unordered_map<std::uint64_t, Glyph> glyphs_;
    std::uint32_t glyphs_generation_ = 0;
    int family_changes_ = 0;
    Rml::CallbackTextureSource atlas_texture_;
    Rml::FontMetrics no_metrics_{};
};

}  // namespace sc::rml
