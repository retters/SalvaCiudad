#include "mods/mod_manifest.h"

#include <charconv>
#include <format>

#include "core/json.h"

namespace sc::mods {

namespace {

bool parse_int(std::string_view text, int& out) {
    if (text.empty() || text.size() > 6) {
        return false;
    }
    const auto r = std::from_chars(text.data(), text.data() + text.size(), out);
    return r.ec == std::errc{} && r.ptr == text.data() + text.size() && out >= 0;
}

// Reads a list of strings; each must pass `valid`.
bool read_list(yyjson_mut_val* obj, const char* key, std::vector<std::string>& out, bool (*valid)(std::string_view),
               std::vector<std::string>& errors) {
    yyjson_mut_val* arr = yyjson_mut_obj_get(obj, key);
    if (arr == nullptr) {
        return true;
    }
    if (!yyjson_mut_is_arr(arr) || yyjson_mut_arr_size(arr) > limits::kMaxListItems) {
        errors.push_back(std::format("'{}' must be a list of at most {} texts", key, limits::kMaxListItems));
        return false;
    }
    std::size_t idx = 0;
    std::size_t max = 0;
    yyjson_mut_val* item = nullptr;
    yyjson_mut_arr_foreach(arr, idx, max, item) {
        const char* s = yyjson_mut_get_str(item);
        if (s == nullptr || std::string_view(s).size() > limits::kMaxTextBytes || !valid(s)) {
            errors.push_back(std::format("'{}' has an invalid entry", key));
            return false;
        }
        out.emplace_back(s);
    }
    return true;
}

bool any_text(std::string_view text) {
    return !text.empty();
}

}  // namespace

bool parse_version(std::string_view text, Version& out) {
    const std::size_t a = text.find('.');
    const std::size_t b = a == std::string_view::npos ? a : text.find('.', a + 1);
    if (a == std::string_view::npos || b == std::string_view::npos) {
        return false;
    }
    Version v;
    if (!parse_int(text.substr(0, a), v.major) || !parse_int(text.substr(a + 1, b - a - 1), v.minor) ||
        !parse_int(text.substr(b + 1), v.patch)) {
        return false;
    }
    out = v;
    return true;
}

std::string version_text(const Version& v) {
    return std::format("{}.{}.{}", v.major, v.minor, v.patch);
}

bool VersionRange::contains(const Version& v) const {
    return v >= min && (!has_max || v < max);
}

bool parse_range(std::string_view text, VersionRange& out) {
    VersionRange r;
    bool any = false;
    while (!text.empty()) {
        const std::size_t space = text.find(' ');
        const std::string_view part = text.substr(0, space);
        text = space == std::string_view::npos ? std::string_view{} : text.substr(space + 1);
        if (part.empty()) {
            continue;
        }
        if (part.starts_with(">=")) {
            if (!parse_version(part.substr(2), r.min)) {
                return false;
            }
        } else if (part.starts_with("<")) {
            if (!parse_version(part.substr(1), r.max)) {
                return false;
            }
            r.has_max = true;
        } else {
            return false;
        }
        any = true;
    }
    if (!any) {
        return false;
    }
    out = r;
    return true;
}

bool is_valid_mod_id(std::string_view id) {
    if (id.empty() || id.size() > limits::kMaxIdBytes) {
        return false;
    }
    for (const char c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) {
            return false;
        }
    }
    return true;
}

bool parse_manifest(std::string_view json_text, ModManifest& out, std::vector<std::string>& errors) {
    if (json_text.size() > limits::kMaxManifestBytes) {
        errors.emplace_back("mod.json is too large");
        return false;
    }
    json::ParseResult parsed = json::parse_object(json_text);
    if (parsed.error != json::ParseError::None) {
        errors.push_back("mod.json is not valid JSON: " + parsed.message);
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    ModManifest m;
    std::int64_t schema = 0;
    if (json::get_int(root, "schemaVersion", 1, 1000, schema) != json::Field::Ok || schema != 1) {
        errors.emplace_back("mod.json needs \"schemaVersion\": 1");
    }
    if (json::get_string(root, "id", limits::kMaxIdBytes, m.id) != json::Field::Ok || !is_valid_mod_id(m.id)) {
        errors.emplace_back("\"id\" must be 1 to 32 characters of a-z, 0-9 and _");
    }
    if (json::get_string(root, "name", limits::kMaxTextBytes, m.name_key) != json::Field::Ok) {
        errors.emplace_back("\"name\" (a text key) is required");
    }
    (void)json::get_string(root, "description", limits::kMaxTextBytes, m.description_key);
    std::string text;
    if (json::get_string(root, "version", 32, text) != json::Field::Ok || !parse_version(text, m.version)) {
        errors.emplace_back("\"version\" must look like 1.0.0");
    }
    text.clear();
    if (json::get_string(root, "gameVersion", 64, text) != json::Field::Ok || !parse_range(text, m.game_version)) {
        errors.emplace_back("\"gameVersion\" must look like \">=0.7.0\" or \">=0.7.0 <1.0.0\"");
    }
    if (json::get_bool(root, "affectsSimulation", m.affects_simulation) == json::Field::Invalid) {
        errors.emplace_back("\"affectsSimulation\" must be true or false");
    }
    (void)read_list(root, "authors", m.authors, any_text, errors);
    (void)read_list(root, "dependencies", m.dependencies, is_valid_mod_id, errors);
    (void)read_list(root, "loadAfter", m.load_after, is_valid_mod_id, errors);
    if (!errors.empty()) {
        return false;
    }
    out = std::move(m);
    return true;
}

}  // namespace sc::mods
