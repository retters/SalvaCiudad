#include "i18n/catalog.h"

#include "core/json.h"
#include "core/text.h"

namespace sc::i18n {

namespace lim = catalog_limits;

bool is_valid_key(std::string_view key) {
    if (key.empty() || key.size() > lim::kMaxKeyBytes || key.front() == '.' || key.back() == '.') {
        return false;
    }
    for (const char c : key) {
        const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '.';
        if (!ok) {
            return false;
        }
    }
    return true;
}

bool is_valid_text(std::string_view text) {
    if (text.size() > lim::kMaxTextBytes) {
        return false;
    }
    // Check line by line so '\n' is the only control character allowed.
    std::size_t start = 0;
    while (true) {
        const std::size_t nl = text.find('\n', start);
        const std::string_view line = text.substr(start, nl == std::string_view::npos ? std::string_view::npos : nl - start);
        if (!text::is_safe_display_text(line, lim::kMaxTextBytes)) {
            return false;
        }
        if (nl == std::string_view::npos) {
            return true;
        }
        start = nl + 1;
    }
}

const std::string& Entry::text(PluralCategory c) const {
    const auto& form = forms[static_cast<std::size_t>(c)];
    return form ? *form : *forms[static_cast<std::size_t>(PluralCategory::Other)];
}

const Entry* Catalog::find(std::string_view key) const {
    const auto it = entries_.find(std::string(key));
    return it == entries_.end() ? nullptr : &it->second;
}

namespace {

std::string_view val_string(yyjson_mut_val* v) {
    return {yyjson_mut_get_str(v), yyjson_mut_get_len(v)};
}

bool read_language(yyjson_mut_val* root, LanguageInfo& info, std::string& error) {
    yyjson_mut_val* lang = nullptr;
    if (json::get_object(root, "language", lang) != json::Field::Ok) {
        error = "missing 'language' object";
        return false;
    }
    std::string code;
    if (json::get_string(lang, "code", 32, code) != json::Field::Ok || code == "auto" ||
        !text::is_valid_language_setting(code)) {
        error = "invalid 'language.code'";
        return false;
    }
    info.code = code;
    if (json::get_string(lang, "name", lim::kMaxNameBytes, info.native_name) != json::Field::Ok ||
        info.native_name.empty()) {
        error = "invalid 'language.name'";
        return false;
    }
    std::string rule;
    const auto parsed_rule = json::get_string(lang, "pluralRule", 32, rule) == json::Field::Ok
                                 ? plural_rule_from_id(rule)
                                 : std::nullopt;
    if (!parsed_rule) {
        error = "missing or unknown 'language.pluralRule'";
        return false;
    }
    info.plural_rule = *parsed_rule;
    // Number formatting is optional; invalid values keep the defaults.
    std::string sep;
    if (json::get_string(lang, "decimalSeparator", lim::kMaxSeparatorBytes, sep) == json::Field::Ok && !sep.empty()) {
        info.decimal_separator = sep;
    }
    sep.clear();
    if (json::get_string(lang, "groupSeparator", lim::kMaxSeparatorBytes, sep) == json::Field::Ok) {
        info.group_separator = sep;
    }
    std::int64_t min_group = 1;
    if (json::get_int(lang, "minimumGroupingDigits", 1, 4, min_group) == json::Field::Ok) {
        info.minimum_grouping_digits = static_cast<int>(min_group);
    }
    return true;
}

// Reads one entry: a string, or an object of plural forms with "other".
bool read_entry(yyjson_mut_val* v, Entry& entry) {
    if (yyjson_mut_is_str(v)) {
        const std::string_view s = val_string(v);
        if (!is_valid_text(s)) {
            return false;
        }
        entry.forms[static_cast<std::size_t>(PluralCategory::Other)] = std::string(s);
        return true;
    }
    if (!yyjson_mut_is_obj(v)) {
        return false;
    }
    yyjson_mut_obj_iter it = yyjson_mut_obj_iter_with(v);
    yyjson_mut_val* key = nullptr;
    while ((key = yyjson_mut_obj_iter_next(&it)) != nullptr) {
        yyjson_mut_val* form = yyjson_mut_obj_iter_get_val(key);
        const auto category = plural_category_from_name(val_string(key));
        if (!category || !yyjson_mut_is_str(form) || !is_valid_text(val_string(form))) {
            return false;
        }
        entry.forms[static_cast<std::size_t>(*category)] = std::string(val_string(form));
    }
    return entry.forms[static_cast<std::size_t>(PluralCategory::Other)].has_value();
}

}  // namespace

CatalogLoadResult Catalog::load(std::string_view json_text) {
    CatalogLoadResult result;
    info_ = LanguageInfo{};
    entries_.clear();

    if (json_text.size() > lim::kMaxFileBytes) {
        result.error = "file too large";
        return result;
    }
    json::ParseResult parsed = json::parse_object(json_text);
    if (parsed.error != json::ParseError::None) {
        result.error = parsed.message;
        return result;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    std::int64_t version = 0;
    if (json::get_int(root, "schemaVersion", 1, INT32_MAX, version) != json::Field::Ok) {
        result.error = "missing or invalid 'schemaVersion'";
        return result;
    }
    if (version > lim::kSchemaVersion) {
        // A newer format might change meanings; better the fallback language.
        result.error = "written for a newer version of the game";
        return result;
    }
    if (!read_language(root, info_, result.error)) {
        return result;
    }
    yyjson_mut_val* strings = nullptr;
    if (json::get_object(root, "strings", strings) != json::Field::Ok) {
        result.error = "missing 'strings' object";
        return result;
    }
    if (yyjson_mut_obj_size(strings) > lim::kMaxEntries) {
        result.error = "too many entries";
        return result;
    }
    yyjson_mut_obj_iter it = yyjson_mut_obj_iter_with(strings);
    yyjson_mut_val* key = nullptr;
    while ((key = yyjson_mut_obj_iter_next(&it)) != nullptr) {
        const std::string_view k = val_string(key);
        Entry entry;
        if (!is_valid_key(k) || entries_.contains(std::string(k)) ||
            !read_entry(yyjson_mut_obj_iter_get_val(key), entry)) {
            ++result.ignored_entries;
            continue;
        }
        entries_.emplace(std::string(k), std::move(entry));
    }
    result.ok = true;
    return result;
}

}  // namespace sc::i18n
