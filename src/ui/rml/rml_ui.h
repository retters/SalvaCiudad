// The player's interface with RmlUi (phases 117 to 127, section 7.14): one
// RmlUi context over the whole window, its documents, and the bridge to
// SDL's events. The rendering itself is whatever RenderInterface it is given
// (the GPU one in the game, a null one in the tests).
//
// Phase 117 only has a test window, shown from the developer tools, next to
// the old interface.
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
    // (hidden or shown) and reloaded with the language.
    bool show_document(const std::string& path, bool show);
    [[nodiscard]] bool document_shown(const std::string& path) const;
    // The loaded document, or null.
    [[nodiscard]] Rml::ElementDocument* document(const std::string& path) const;
    void show_debugger(bool show);
    [[nodiscard]] bool debugger_shown() const { return debugger_shown_; }

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
    [[nodiscard]] Document* find(const std::string& path);

    System system_;
    Files files_;
    std::unique_ptr<FontEngine> font_engine_;
    Rml::Context* context_ = nullptr;
    std::vector<Document> documents_;
    std::uint64_t language_generation_ = 0;
    bool family_changed_ = false;
    bool debugger_ready_ = false;
    bool debugger_shown_ = false;
    bool pressed_ = false;  // A button went down over an element.
    double update_ms_ = 0.0;
    double render_ms_ = 0.0;
};

}  // namespace sc::rml
