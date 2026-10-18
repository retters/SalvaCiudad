#include "ui/rml/rml_system.h"

#include <algorithm>
#include <memory>

#include <SDL3/SDL_clipboard.h>
#include <SDL3/SDL_stdinc.h>
#include <SDL3/SDL_timer.h>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"
#include "i18n/translator.h"

namespace sc::rml {

namespace {

bool key_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' ||
           c == '.';
}

}  // namespace

int translate_keys(std::string_view text, const KeyLookup& lookup, std::string& out) {
    out.clear();
    out.reserve(text.size());
    int replaced = 0;
    std::size_t i = 0;
    while (i < text.size()) {
        if (text[i] != '@') {
            out += text[i++];
            continue;
        }
        std::size_t end = i + 1;
        while (end < text.size() && key_char(text[end])) {
            ++end;
        }
        // A key ends on a letter or digit: "@a.b." keeps its last dot as text.
        while (end > i + 1 && (text[end - 1] == '.' || text[end - 1] == '-')) {
            --end;
        }
        const std::string_view key = text.substr(i + 1, end - i - 1);
        if (key.find('.') != std::string_view::npos) {
            if (const std::optional<std::string> value = lookup(key)) {
                out += *value;
                ++replaced;
                i = end;
                continue;
            }
        }
        out += '@';
        ++i;
    }
    return replaced;
}

double System::GetElapsedTime() {
    return static_cast<double>(SDL_GetTicksNS()) * 1e-9;
}

int System::TranslateString(Rml::String& translated, const Rml::String& input) {
    if (input.find('@') == Rml::String::npos) {
        translated = input;
        return 0;
    }
    const i18n::Translator& tr = i18n::translator();
    return translate_keys(
        input,
        [&tr](std::string_view key) -> std::optional<std::string> {
            if (!tr.has(key)) {
                return std::nullopt;
            }
            return tr.text(key);
        },
        translated);
}

bool System::LogMessage(Rml::Log::Type type, const Rml::String& message) {
    switch (type) {
        case Rml::Log::LT_ERROR:
        case Rml::Log::LT_ASSERT:
            ++errors_;
            log::error("rmlui: {}", message);
            break;
        case Rml::Log::LT_WARNING:
            // When a data-for list gets shorter, RmlUi still updates the views of
            // the copies it is removing in that same pass, and they read past the
            // end once (D-12506): harmless, so only for the developer's log.
            if (message.starts_with("Data array index out of bounds") ||
                (message.starts_with("Could not get value from data variable '") && message.find('[') != Rml::String::npos)) {
                log::debug("rmlui: {}", message);
                break;
            }
            ++warnings_;
            log::warn("rmlui: {}", message);
            break;
        default:
            break;  // Info and debug messages stay out of the log.
    }
    return true;
}

void System::SetClipboardText(const Rml::String& text) {
    (void)SDL_SetClipboardText(text.c_str());
}

void System::GetClipboardText(Rml::String& text) {
    char* clip = SDL_GetClipboardText();
    text = clip != nullptr ? clip : "";
    SDL_free(clip);
}

std::optional<std::filesystem::path> resolve_ui_path(const std::vector<std::filesystem::path>& roots,
                                                     std::string_view path) {
    if (path.empty() || path.size() > 512 || path.front() == '/' || path.front() == '\\' ||
        path.find(':') != std::string_view::npos || path.find('\0') != std::string_view::npos) {
        return std::nullopt;
    }
    // Every part must be a plain name: no "..", ".", or empty parts.
    std::size_t start = 0;
    while (start <= path.size()) {
        const std::size_t slash = path.find_first_of("/\\", start);
        const std::size_t stop = slash == std::string_view::npos ? path.size() : slash;
        const std::string_view part = path.substr(start, stop - start);
        if (part.empty() || part == "." || part == "..") {
            return std::nullopt;
        }
        if (slash == std::string_view::npos) {
            break;
        }
        start = slash + 1;
    }
    const std::filesystem::path relative = text::path_from_utf8(path);
    for (const std::filesystem::path& root : roots) {
        std::error_code ec;
        const std::filesystem::path base = std::filesystem::weakly_canonical(root, ec);
        if (ec) {
            continue;
        }
        const std::filesystem::path full = std::filesystem::weakly_canonical(base / relative, ec);
        if (ec || !std::filesystem::is_regular_file(full, ec)) {
            continue;
        }
        // A link may not lead outside its root.
        const auto [root_end, full_it] = std::mismatch(base.begin(), base.end(), full.begin(), full.end());
        if (root_end == base.end()) {
            return full;
        }
    }
    return std::nullopt;
}

Rml::FileHandle Files::Open(const Rml::String& path) {
    if (path == kStyleSheet && style_sheet_) {
        return reinterpret_cast<Rml::FileHandle>(new OpenFile{style_sheet_(), 0});
    }
    const std::optional<std::filesystem::path> full = resolve_ui_path(roots_, path);
    if (!full) {
        log::warn("rmlui: refused or missing file '{}'", path);
        return 0;
    }
    fs::ReadResult r = fs::read_file(*full, kMaxFileBytes);
    if (r.error != fs::IoError::None) {
        log::warn("rmlui: cannot read '{}': {}", path, fs::io_error_name(r.error));
        return 0;
    }
    if (filter_ && path.size() > 5 && path.ends_with(".rcss")) {
        filter_(path, r.data);
    }
    auto* file = new OpenFile{std::move(r.data), 0};
    return reinterpret_cast<Rml::FileHandle>(file);
}

void Files::Close(Rml::FileHandle file) {
    delete reinterpret_cast<OpenFile*>(file);
}

size_t Files::Read(void* buffer, size_t size, Rml::FileHandle file) {
    auto* f = reinterpret_cast<OpenFile*>(file);
    const std::size_t n = std::min(size, f->data.size() - f->position);
    std::copy_n(f->data.data() + f->position, n, static_cast<char*>(buffer));
    f->position += n;
    return n;
}

bool Files::Seek(Rml::FileHandle file, long offset, int origin) {
    auto* f = reinterpret_cast<OpenFile*>(file);
    long long base = 0;
    if (origin == SEEK_CUR) {
        base = static_cast<long long>(f->position);
    } else if (origin == SEEK_END) {
        base = static_cast<long long>(f->data.size());
    }
    const long long target = base + offset;
    if (target < 0 || target > static_cast<long long>(f->data.size())) {
        return false;
    }
    f->position = static_cast<std::size_t>(target);
    return true;
}

size_t Files::Tell(Rml::FileHandle file) {
    return reinterpret_cast<OpenFile*>(file)->position;
}

size_t Files::Length(Rml::FileHandle file) {
    return reinterpret_cast<OpenFile*>(file)->data.size();
}

}  // namespace sc::rml
