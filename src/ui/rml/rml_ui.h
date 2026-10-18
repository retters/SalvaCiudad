// The player's interface with RmlUi (phases 117 to 127, section 7.14): one
// RmlUi context over the whole window, its documents, and the bridge to
// SDL's events. The rendering itself is whatever RenderInterface it is given
// (the GPU one in the game, a null one in the tests).
//
// Phase 117 only has a test window, shown from the developer tools, next to
// the old interface. Phase 119 adds the styles: the active one fills the
// tokens of every sheet and gives /style.rcss and the icons' sprite sheet.
#pragma once

#include <SDL3/SDL_events.h>

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include <RmlUi/Core/Context.h>
#include <RmlUi/Core/RenderInterface.h>

#include "ui/font_library.h"
#include "ui/glyph_atlas.h"
#include "ui/rml/rml_font_engine.h"
#include "ui/rml/rml_style.h"
#include "ui/rml/rml_system.h"

namespace sc::rml {

class RmlUi {
public:
    RmlUi() = default;
    ~RmlUi();
    RmlUi(const RmlUi&) = delete;
    RmlUi& operator=(const RmlUi&) = delete;

    // `roots` are the folders documents may be read from (data/ui first).
    // Only one RmlUi may be alive at a time: RmlUi itself is global.
    bool init(Rml::RenderInterface& render, ui::GlyphAtlas& atlas, const ui::FontLibrary& fonts,
              std::vector<std::filesystem::path> roots, std::string_view ui_family);
    void shutdown();
    [[nodiscard]] bool ready() const { return context_ != nullptr; }
    [[nodiscard]] Rml::Context* context() const { return context_; }

    // The interface family of the settings; documents reload if it changed.
    void set_ui_family(std::string_view id);

    // The roots again (data/ui and the active mods' ui folders): the styles
    // are looked for again and the documents reload.
    void set_roots(std::vector<std::filesystem::path> roots);
    // Every valid style, and the active one: `id`, or Frosted if there is no
    // such style. Returns the id in use; documents reload on the next update.
    [[nodiscard]] const StyleLibrary& styles() const { return styles_; }
    std::string set_style(std::string_view id);
    [[nodiscard]] const std::string& style_id() const { return style_id_; }
    [[nodiscard]] const TokenMap& tokens() const { return tokens_; }

    // Per frame, after the events: lays out the documents (reloading them if
    // the language or the font changed) and then hands their geometry to the
    // render interface.
    void update(int width, int height, float dp_ratio);
    void render();

    // Gives an SDL event to RmlUi. True if the interface took it, so the old
    // interface and the camera must not see it.
    bool process_event(const SDL_Event& event, float pixel_density);
    // True while the pointer is over (or dragging from) one of its elements.
    [[nodiscard]] bool wants_mouse() const;
    // True while a text field has the keyboard.
    [[nodiscard]] bool wants_keyboard() const;

    // A document by its path under the roots ("dev/prueba.rml"); kept open
    // (hidden or shown) and reloaded with the language. "path#N" is another
    // copy of the same document (one under "dev/" is moved N times 32 dp
    // right and down, to see them apart).
    bool show_document(const std::string& path, bool show);
    [[nodiscard]] bool document_shown(const std::string& path) const;
    // Unloads every document (they load again when shown).
    void close_documents();
    // The loaded document, or null.
    [[nodiscard]] Rml::ElementDocument* document(const std::string& path) const;
    void show_debugger(bool show);
    [[nodiscard]] bool debugger_shown() const { return debugger_shown_; }

    // The simple glass (phase 118): every document's body gets the class
    // "glass-simple", so its style can make the windows more opaque.
    void set_simple_glass(bool simple);

    // Tooltips (phase 121): the "tip" attribute of the element under the
    // pointer (or of the nearest parent that has one) shows after `delay_ms`
    // in hud/tooltip.rml; "tip-detail" is shown under it while Shift is
    // held. Texts may hold @keys and are split into lines at '\n'.
    void set_tooltips(bool show, int delay_ms) {
        tooltips_on_ = show;
        tooltip_delay_ms_ = delay_ms;
    }
    static constexpr const char* kTooltipDocument = "hud/tooltip.rml";
    // What the tooltip shows now (empty: none), for the tests.
    [[nodiscard]] const std::string& tooltip_shown() const { return tooltip_shown_; }
    // The tutorial's pointer (phase 121): every element whose "mark"
    // attribute is `key` gets the class "marked". Empty: none.
    void set_mark(std::string key) { mark_ = std::move(key); }

    [[nodiscard]] const System& system() const { return system_; }
    // Milliseconds of CPU the last update() and render() took.
    [[nodiscard]] double update_ms() const { return update_ms_; }
    [[nodiscard]] double render_ms() const { return render_ms_; }

private:
    struct Document {
        std::string path;
        Rml::ElementDocument* document = nullptr;
        bool shown = false;
    };
    void reload_documents();
    void prepare(Document& d);
    void scan_styles();
    void update_tooltip();
    void apply_marks();
    void build_style_sheet();
    [[nodiscard]] bool simple_glass_class() const;
    [[nodiscard]] Document* find(const std::string& path);

    System system_;
    Files files_;
    std::unique_ptr<FontEngine> font_engine_;
    Rml::Context* context_ = nullptr;
    std::vector<Document> documents_;
    std::uint64_t language_generation_ = 0;
    bool family_changed_ = false;
    bool debugger_ready_ = false;
    bool simple_glass_ = false;
    const ui::FontLibrary* fonts_ = nullptr;
    StyleLibrary styles_;
    std::string style_id_;
    TokenMap tokens_ = default_tokens();
    std::string style_sheet_;
    int icon_scale_ = 1;     // The icons' sprite sheet: 1x or 2x.
    bool style_changed_ = false;
    bool tooltips_on_ = true;
    int tooltip_delay_ms_ = 500;
    float mouse_x_ = 0.0f;
    float mouse_y_ = 0.0f;
    Rml::Element* tip_element_ = nullptr;
    std::string tip_text_;
    std::uint64_t tip_since_ns_ = 0;
    std::string tooltip_shown_;  // Its RML now.
    std::string mark_;
    bool debugger_shown_ = false;
    bool pressed_ = false;  // A button went down over an element.
    double update_ms_ = 0.0;
    double render_ms_ = 0.0;
};

}  // namespace sc::rml
