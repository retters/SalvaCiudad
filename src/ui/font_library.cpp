#include "ui/font_library.h"

#include "core/file_io.h"
#include "core/json.h"
#include "core/log.h"
#include "core/text.h"

namespace sc::ui {

namespace {

constexpr std::size_t kMaxManifestBytes = 64u * 1024u;
constexpr std::size_t kMaxFamilies = 32;

// A relative path inside the fonts folder: no "..", no root, no drive.
bool is_safe_relative_path(std::string_view s) {
    if (s.empty() || s.size() > 200 || !text::is_safe_display_text(s, 200) || s.front() == '/' ||
        s.front() == '\\' || s.find(':') != std::string_view::npos || s.find('\\') != std::string_view::npos) {
        return false;
    }
    std::size_t start = 0;
    while (start <= s.size()) {
        const std::size_t slash = s.find('/', start);
        const std::string_view part = s.substr(start, slash == std::string_view::npos ? std::string_view::npos : slash - start);
        if (part.empty() || part == "." || part == "..") {
            return false;
        }
        if (slash == std::string_view::npos) {
            return true;
        }
        start = slash + 1;
    }
    return true;
}

std::unique_ptr<Font> load_font(const std::filesystem::path& dir, std::string_view relative) {
    if (!is_safe_relative_path(relative)) {
        log::warn("fonts: rejected path '{}'", relative);
        return nullptr;
    }
    const fs::ReadResult r = fs::read_file(dir / text::path_from_utf8(relative), Font::kMaxFileBytes);
    if (r.error != fs::IoError::None) {
        log::warn("fonts: cannot read '{}' ({})", relative, fs::io_error_name(r.error));
        return nullptr;
    }
    auto font = std::make_unique<Font>();
    if (!font->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end()))) {
        log::warn("fonts: '{}' is not a usable TrueType font", relative);
        return nullptr;
    }
    return font;
}

bool is_valid_id(std::string_view id) {
    if (id.empty() || id.size() > 64) {
        return false;
    }
    for (const char c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
            return false;
        }
    }
    return true;
}

}  // namespace

bool FontLibrary::load(const std::filesystem::path& fonts_dir) {
    ui_families_.clear();
    logo_.reset();
    const fs::ReadResult manifest = fs::read_file(fonts_dir / "fonts.json", kMaxManifestBytes);
    if (manifest.error != fs::IoError::None) {
        log::error("fonts: cannot read fonts.json ({})", fs::io_error_name(manifest.error));
        return false;
    }
    json::ParseResult parsed = json::parse_object(manifest.data);
    if (parsed.error != json::ParseError::None) {
        log::error("fonts: fonts.json is not valid ({})", parsed.message);
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    yyjson_mut_val* list = yyjson_mut_obj_get(root, "fonts");
    if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > kMaxFamilies) {
        log::error("fonts: fonts.json needs a 'fonts' list of at most {} entries", kMaxFamilies);
        return false;
    }
    for (std::size_t i = 0; i < yyjson_mut_arr_size(list); ++i) {
        yyjson_mut_val* entry = yyjson_mut_arr_get(list, i);
        std::string id;
        std::string name;
        std::string role;
        std::string regular;
        std::string bold;
        if (json::get_string(entry, "id", 64, id) != json::Field::Ok || !is_valid_id(id) ||
            json::get_string(entry, "name", 64, name) != json::Field::Ok ||
            json::get_string(entry, "role", 16, role) != json::Field::Ok ||
            json::get_string(entry, "regular", 200, regular) != json::Field::Ok) {
            log::warn("fonts: entry {} in fonts.json is invalid, skipped", i);
            continue;
        }
        auto regular_font = load_font(fonts_dir, regular);
        if (!regular_font) {
            continue;
        }
        if (role == "logo") {
            logo_ = std::move(regular_font);
        } else if (role == "ui") {
            FontFamily family;
            family.id = id;
            family.name = name;
            family.regular = std::move(regular_font);
            if (json::get_string(entry, "bold", 200, bold) == json::Field::Ok) {
                family.bold = load_font(fonts_dir, bold);
            }
            ui_families_.push_back(std::move(family));
        } else {
            log::warn("fonts: unknown role '{}' for '{}', skipped", role, id);
        }
    }
    log::info("fonts: {} interface famil(y/ies), logo font {}", ui_families_.size(), logo_ ? "loaded" : "missing");
    return !ui_families_.empty();
}

const FontFamily* FontLibrary::ui_family(std::string_view id) const {
    for (const FontFamily& f : ui_families_) {
        if (f.id == id) {
            return &f;
        }
    }
    return ui_families_.empty() ? nullptr : &ui_families_.front();
}

}  // namespace sc::ui
