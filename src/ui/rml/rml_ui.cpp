#include "ui/rml/rml_ui.h"

#include <format>

#include <SDL3/SDL_keyboard.h>
#include <SDL3/SDL_timer.h>

#include <RmlUi/Core/Core.h>
#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Factory.h>
#include <RmlUi/Debugger/Debugger.h>

#include "core/file_io.h"
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
    files_.set_sheet_hooks([this] { return style_sheet_; },
                           [this](const std::string& path, std::string& text) {
                               std::vector<std::string> unknown;
                               text = substitute_tokens(text, tokens_, &unknown);
                               for (const std::string& name : unknown) {
                                   log::warn("rmlui: '{}' uses the unknown token '{}'", path, name);
                               }
                           });
    fonts_ = &fonts;
    scan_styles();
    (void)set_style(kDefaultStyle);
    style_changed_ = false;
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

void RmlUi::scan_styles() {
    const FontCheck fonts = [this](std::string_view id) {
        if (fonts_ != nullptr) {
            for (const ui::FontFamily& f : fonts_->ui_families()) {
                if (f.id == id) {
                    return true;
                }
            }
        }
        return false;
    };
    styles_.scan(files_.roots(), fonts);
    for (const std::string& error : styles_.errors()) {
        log::warn("rmlui: style rejected: {}", error);
    }
}

void RmlUi::build_style_sheet() {
    const Style* style = styles_.find(style_id_);
    style_sheet_ = style != nullptr ? style->sheet : std::string();
    // The icons in the style's mode and the size the scale needs, from the
    // game's own folder (tools/ui/iconos.py writes them).
    const std::string icons = std::format("icons/{}@{}x.rcss", tokens_.at("icon-mode"), icon_scale_);
    const std::optional<std::filesystem::path> file = resolve_ui_path({files_.roots().front()}, icons);
    const fs::ReadResult r = file ? fs::read_file(*file, Files::kMaxFileBytes) : fs::ReadResult{};
    if (!file || r.error != fs::IoError::None) {
        log::warn("rmlui: no icon sheet '{}'", icons);
        return;
    }
    style_sheet_ += r.data;
}

std::string RmlUi::set_style(std::string_view id) {
    const Style* style = styles_.find(id);
    if (style == nullptr) {
        if (!id.empty() && id != kDefaultStyle) {
            log::warn("rmlui: no style '{}'; using {}", id, kDefaultStyle);
        }
        style = styles_.find(kDefaultStyle);
    }
    if (style == nullptr && !styles_.styles().empty()) {
        style = &styles_.styles().front();
    }
    const std::string chosen = style != nullptr ? style->id : std::string();
    if (chosen == style_id_ && !style_sheet_.empty()) {
        return chosen;
    }
    style_id_ = chosen;
    tokens_ = style != nullptr ? style->tokens : default_tokens();
    build_style_sheet();
    style_changed_ = true;
    return chosen;
}

void RmlUi::set_roots(std::vector<std::filesystem::path> roots) {
    if (roots == files_.roots()) {
        return;
    }
    files_.set_roots(std::move(roots));
    scan_styles();
    const std::string wanted = style_id_;
    style_id_.clear();
    (void)set_style(wanted);
}

bool RmlUi::simple_glass_class() const {
    const Style* style = styles_.find(style_id_);
    return simple_glass_ || (style != nullptr && !style->glass);
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
        Rml::ElementDocument* doc = context_->LoadDocument(path.substr(0, path.find('#')));
        if (doc == nullptr) {
            log::warn("rmlui: cannot load the document '{}'", path);
            return false;
        }
        documents_.push_back({path, doc, false});
        d = &documents_.back();
        prepare(*d);
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

void RmlUi::prepare(Document& d) {
    d.document->SetClass("glass-simple", simple_glass_class());
    const std::size_t hash = d.path.find('#');
    if (hash == std::string::npos) {
        return;
    }
    int n = 0;
    for (std::size_t i = hash + 1; i < d.path.size() && i < hash + 3; ++i) {
        if (d.path[i] < '0' || d.path[i] > '9') {
            return;
        }
        n = n * 10 + (d.path[i] - '0');
    }
    const std::string offset = std::to_string(n * 32) + "dp";
    d.document->SetProperty("margin-left", offset);
    d.document->SetProperty("margin-top", offset);
}

void RmlUi::close_documents() {
    if (context_ == nullptr) {
        return;
    }
    for (const Document& d : documents_) {
        context_->UnloadDocument(d.document);
    }
    documents_.clear();
    context_->Update();  // Unloading takes effect on the next update.
}

void RmlUi::set_simple_glass(bool simple) {
    if (simple == simple_glass_) {
        return;
    }
    simple_glass_ = simple;
    for (const Document& d : documents_) {
        d.document->SetClass("glass-simple", simple_glass_class());
    }
}

void RmlUi::reload_documents() {
    for (Document& d : documents_) {
        context_->UnloadDocument(d.document);
    }
    context_->Update();  // Unloading takes effect on the next update.
    for (Document& d : documents_) {
        d.document = context_->LoadDocument(d.path.substr(0, d.path.find('#')));
        if (d.document == nullptr) {
            continue;
        }
        prepare(d);
        if (d.shown) {
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
    // Icons drawn at twice the size from a scale of 1.5 up.
    const int icon_scale = dp_ratio >= 1.5f ? 2 : 1;
    if (icon_scale != icon_scale_) {
        icon_scale_ = icon_scale;
        build_style_sheet();
        style_changed_ = true;
    }
    const std::uint64_t generation = i18n::translator().generation();
    if (generation != language_generation_ || family_changed_ || style_changed_) {
        if (style_changed_) {
            Rml::Factory::ClearStyleSheetCache();  // The sheets read again, with the new tokens.
        }
        language_generation_ = generation;
        family_changed_ = false;
        style_changed_ = false;
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
