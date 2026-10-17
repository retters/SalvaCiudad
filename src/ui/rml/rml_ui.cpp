#include "ui/rml/rml_ui.h"

#include <SDL3/SDL_keyboard.h>
#include <SDL3/SDL_timer.h>

#include <RmlUi/Core/Core.h>
#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Debugger/Debugger.h>

#include "core/log.h"
#include "i18n/translator.h"
#include "ui/rml/rml_input.h"

namespace sc::rml {

namespace {

double ms_since(std::uint64_t start_ns) {
    return static_cast<double>(SDL_GetTicksNS() - start_ns) * 1e-6;
}

}  // namespace

RmlUi::~RmlUi() {
    shutdown();
}

bool RmlUi::init(Rml::RenderInterface& render, ui::GlyphAtlas& atlas, const ui::FontLibrary& fonts,
                 std::vector<std::filesystem::path> roots, std::string_view ui_family) {
    files_.set_roots(std::move(roots));
    font_engine_ = std::make_unique<FontEngine>(atlas, fonts);
    font_engine_->set_ui_family(ui_family);
    Rml::SetSystemInterface(&system_);
    Rml::SetFileInterface(&files_);
    Rml::SetFontEngineInterface(font_engine_.get());
    Rml::SetRenderInterface(&render);
    if (!Rml::Initialise()) {
        log::error("rmlui: cannot initialise");
        return false;
    }
    context_ = Rml::CreateContext("main", Rml::Vector2i(1280, 720));
    if (context_ == nullptr) {
        log::error("rmlui: cannot create the context");
        Rml::Shutdown();
        return false;
    }
    language_generation_ = i18n::translator().generation();
    log::info("rmlui: {} ready", Rml::GetVersion());
    return true;
}

void RmlUi::shutdown() {
    if (context_ == nullptr) {
        return;
    }
    documents_.clear();
    if (debugger_ready_) {
        Rml::Debugger::Shutdown();
        debugger_ready_ = false;
    }
    Rml::RemoveContext("main");
    context_ = nullptr;
    Rml::Shutdown();
    font_engine_.reset();
}

void RmlUi::set_ui_family(std::string_view id) {
    if (font_engine_ != nullptr) {
        font_engine_->set_ui_family(id);
        family_changed_ = true;
    }
}

RmlUi::Document* RmlUi::find(const std::string& path) {
    for (Document& d : documents_) {
        if (d.path == path) {
            return &d;
        }
    }
    return nullptr;
}

bool RmlUi::show_document(const std::string& path, bool show) {
    if (context_ == nullptr) {
        return false;
    }
    Document* d = find(path);
    if (d == nullptr) {
        if (!show) {
            return true;
        }
        Rml::ElementDocument* doc = context_->LoadDocument(path);
        if (doc == nullptr) {
            log::warn("rmlui: cannot load the document '{}'", path);
            return false;
        }
        documents_.push_back({path, doc, false});
        d = &documents_.back();
    }
    d->shown = show;
    if (show) {
        d->document->Show();
    } else {
        d->document->Hide();
    }
    return true;
}

bool RmlUi::document_shown(const std::string& path) const {
    for (const Document& d : documents_) {
        if (d.path == path) {
            return d.shown;
        }
    }
    return false;
}

Rml::ElementDocument* RmlUi::document(const std::string& path) const {
    for (const Document& d : documents_) {
        if (d.path == path) {
            return d.document;
        }
    }
    return nullptr;
}

void RmlUi::show_debugger(bool show) {
    if (context_ == nullptr) {
        return;
    }
    if (show && !debugger_ready_) {
        debugger_ready_ = Rml::Debugger::Initialise(context_);
    }
    if (debugger_ready_) {
        Rml::Debugger::SetVisible(show);
        debugger_shown_ = show;
    }
}

void RmlUi::reload_documents() {
    for (Document& d : documents_) {
        context_->UnloadDocument(d.document);
    }
    context_->Update();  // Unloading takes effect on the next update.
    for (Document& d : documents_) {
        d.document = context_->LoadDocument(d.path);
        if (d.document != nullptr && d.shown) {
            d.document->Show();
        }
    }
    std::erase_if(documents_, [](const Document& d) { return d.document == nullptr; });
}

void RmlUi::update(int width, int height, float dp_ratio) {
    if (context_ == nullptr) {
        return;
    }
    const std::uint64_t start = SDL_GetTicksNS();
    if (context_->GetDimensions() != Rml::Vector2i(width, height)) {
        context_->SetDimensions(Rml::Vector2i(width, height));
    }
    if (context_->GetDensityIndependentPixelRatio() != dp_ratio) {
        context_->SetDensityIndependentPixelRatio(dp_ratio);
    }
    const std::uint64_t generation = i18n::translator().generation();
    if (generation != language_generation_ || family_changed_) {
        language_generation_ = generation;
        family_changed_ = false;
        reload_documents();
    }
    context_->Update();
    update_ms_ = ms_since(start);
}

void RmlUi::render() {
    if (context_ == nullptr) {
        return;
    }
    const std::uint64_t start = SDL_GetTicksNS();
    context_->Render();
    render_ms_ = ms_since(start);
}

bool RmlUi::wants_mouse() const {
    if (context_ == nullptr) {
        return false;
    }
    if (pressed_) {
        return true;
    }
    const Rml::Element* hover = context_->GetHoverElement();
    return hover != nullptr && hover != context_->GetRootElement();
}

bool RmlUi::wants_keyboard() const {
    if (context_ == nullptr) {
        return false;
    }
    const Rml::Element* focus = context_->GetFocusElement();
    return focus != nullptr && (focus->GetTagName() == "input" || focus->GetTagName() == "textarea");
}

bool RmlUi::process_event(const SDL_Event& event, float pixel_density) {
    if (context_ == nullptr) {
        return false;
    }
    const int mods = modifiers_from_sdl(SDL_GetModState());
    switch (event.type) {
        case SDL_EVENT_MOUSE_MOTION:
            context_->ProcessMouseMove(static_cast<int>(event.motion.x * pixel_density),
                                       static_cast<int>(event.motion.y * pixel_density), mods);
            return wants_mouse();
        case SDL_EVENT_MOUSE_BUTTON_DOWN: {
            const int button = button_from_sdl(event.button.button);
            if (button < 0 || !wants_mouse()) {
                return false;
            }
            pressed_ = true;
            context_->ProcessMouseButtonDown(button, mods);
            return true;
        }
        case SDL_EVENT_MOUSE_BUTTON_UP: {
            const int button = button_from_sdl(event.button.button);
            const bool mine = pressed_;
            pressed_ = false;
            if (button >= 0) {
                context_->ProcessMouseButtonUp(button, mods);
            }
            return mine;
        }
        case SDL_EVENT_MOUSE_WHEEL:
            if (!wants_mouse()) {
                return false;
            }
            context_->ProcessMouseWheel(Rml::Vector2f(-event.wheel.x, -event.wheel.y), mods);
            return true;
        case SDL_EVENT_WINDOW_MOUSE_LEAVE:
            context_->ProcessMouseLeave();
            return false;
        case SDL_EVENT_KEY_DOWN:
            if (!wants_keyboard()) {
                return false;
            }
            context_->ProcessKeyDown(key_from_sdl(event.key.key), mods);
            return true;
        case SDL_EVENT_KEY_UP:
            if (!wants_keyboard()) {
                return false;
            }
            context_->ProcessKeyUp(key_from_sdl(event.key.key), mods);
            return true;
        case SDL_EVENT_TEXT_INPUT:
            if (!wants_keyboard() || event.text.text == nullptr) {
                return false;
            }
            context_->ProcessTextInput(Rml::String(event.text.text));
            return true;
        default:
            return false;
    }
}

}  // namespace sc::rml
