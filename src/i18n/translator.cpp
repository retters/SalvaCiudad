#include "i18n/translator.h"

#include <algorithm>
#include <system_error>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"

namespace sc::i18n {

namespace {

bool iequals(std::string_view a, std::string_view b) {
    return std::equal(a.begin(), a.end(), b.begin(), b.end(), [](char x, char y) {
        const auto lower = [](char c) { return (c >= 'A' && c <= 'Z') ? static_cast<char>(c - 'A' + 'a') : c; };
        return lower(x) == lower(y);
    });
}

// "es-MX" -> "es"; "zh-Hant-TW" -> "zh-Hant"; "es" -> "".
std::string_view parent_code(std::string_view code) {
    const std::size_t dash = code.rfind('-');
    return dash == std::string_view::npos ? std::string_view{} : code.substr(0, dash);
}

}  // namespace

std::string format_template(std::string_view tmpl, std::span<const std::string> args) {
    std::string out;
    out.reserve(tmpl.size() + 16);
    std::size_t i = 0;
    while (i < tmpl.size()) {
        const char c = tmpl[i];
        if (c == '{' && i + 1 < tmpl.size() && tmpl[i + 1] == '{') {
            out += '{';
            i += 2;
            continue;
        }
        if (c == '}' && i + 1 < tmpl.size() && tmpl[i + 1] == '}') {
            out += '}';
            i += 2;
            continue;
        }
        if (c == '{') {
            const std::size_t close = tmpl.find('}', i + 1);
            if (close != std::string_view::npos) {
                std::string_view inside = tmpl.substr(i + 1, close - i - 1);
                const std::size_t colon = inside.find(':');
                if (colon != std::string_view::npos) {
                    inside = inside.substr(0, colon);
                }
                std::size_t index = 0;
                bool digits = !inside.empty() && inside.size() <= 2;
                for (const char d : inside) {
                    if (d < '0' || d > '9') {
                        digits = false;
                        break;
                    }
                    index = index * 10 + static_cast<std::size_t>(d - '0');
                }
                if (digits && index < args.size()) {
                    out += args[index];
                    i = close + 1;
                    continue;
                }
            }
        }
        out += c;
        ++i;
    }
    return out;
}

std::string format_integer(const LanguageInfo& info, std::int64_t value) {
    const bool negative = value < 0;
    std::uint64_t magnitude = negative ? 0 - static_cast<std::uint64_t>(value) : static_cast<std::uint64_t>(value);
    std::string digits;
    do {
        digits += static_cast<char>('0' + magnitude % 10);
        magnitude /= 10;
    } while (magnitude > 0);
    std::reverse(digits.begin(), digits.end());

    // Group only when the number has at least 3 + minimum_grouping_digits digits.
    const bool group = !info.group_separator.empty() &&
                       digits.size() >= static_cast<std::size_t>(3 + info.minimum_grouping_digits);
    std::string out;
    if (negative) {
        out += '-';
    }
    for (std::size_t k = 0; k < digits.size(); ++k) {
        out += digits[k];
        const std::size_t remaining = digits.size() - k - 1;
        if (group && remaining > 0 && remaining % 3 == 0) {
            out += info.group_separator;
        }
    }
    return out;
}

int Translator::load(const std::filesystem::path& dir, std::string_view builtin_base_json) {
    catalogs_.clear();
    chain_.clear();
    reported_missing_.clear();
    int skipped = 0;
    if (!add_language(builtin_base_json, "built-in")) {
        ++skipped;
    }

    std::error_code ec;
    std::vector<std::filesystem::path> files;
    for (std::filesystem::directory_iterator it(dir, ec), end; !ec && it != end; it.increment(ec)) {
        if (it->is_regular_file(ec) && it->path().extension() == ".json") {
            files.push_back(it->path());
        }
    }
    if (ec) {
        log::warn("i18n: cannot list the language folder ({})", ec.message());
    }
    std::sort(files.begin(), files.end());
    for (const auto& file : files) {
        const fs::ReadResult read = fs::read_file(file, catalog_limits::kMaxFileBytes);
        const std::string name = text::path_to_utf8(file.filename());
        if (read.error != fs::IoError::None) {
            log::warn("i18n: skipped '{}' ({})", name, fs::io_error_name(read.error));
            ++skipped;
        } else if (!add_language(read.data, name)) {
            ++skipped;
        }
    }
    (void)set_language(kBaseLanguage);
    return skipped;
}

bool Translator::add_language(std::string_view json_text, std::string_view origin_for_log) {
    auto catalog = std::make_unique<Catalog>();
    const CatalogLoadResult r = catalog->load(json_text);
    if (!r.ok) {
        log::warn("i18n: skipped language file '{}' ({})", origin_for_log, r.error);
        return false;
    }
    if (r.ignored_entries > 0) {
        log::warn("i18n: '{}' has {} invalid entr(y/ies), ignored", origin_for_log, r.ignored_entries);
    }
    // A file replaces an earlier one with the same code (the built-in base
    // is replaced by data/lang/en.json, which may be newer).
    const std::string code = catalog->info().code;
    std::erase_if(catalogs_, [&](const auto& c) { return iequals(c->info().code, code); });
    catalogs_.push_back(std::move(catalog));
    return true;
}

bool Translator::add_mod_texts(std::string_view json_text, std::string_view origin_for_log) {
    auto catalog = std::make_unique<Catalog>();
    const CatalogLoadResult r = catalog->load(json_text);
    if (!r.ok) {
        log::warn("i18n: skipped mod language file '{}' ({})", origin_for_log, r.error);
        return false;
    }
    if (r.ignored_entries > 0) {
        log::warn("i18n: '{}' has {} invalid entr(y/ies), ignored", origin_for_log, r.ignored_entries);
    }
    mod_catalogs_.push_back(std::move(catalog));
    reported_missing_.clear();
    ++generation_;
    return true;
}

void Translator::clear_mod_texts() {
    mod_catalogs_.clear();
    reported_missing_.clear();
    ++generation_;
}

// A text of one language: the mods' texts first (the last loaded mod
// wins), then the game's own.
const Entry* Translator::find_in(const Catalog* c, std::string_view key) const {
    for (auto it = mod_catalogs_.rbegin(); it != mod_catalogs_.rend(); ++it) {
        if (iequals((*it)->info().code, c->info().code)) {
            if (const Entry* e = (*it)->find(key)) {
                return e;
            }
        }
    }
    return c->find(key);
}

const Catalog* Translator::find_catalog(std::string_view code) const {
    for (const auto& c : catalogs_) {
        if (iequals(c->info().code, code)) {
            return c.get();
        }
    }
    return nullptr;
}

std::string Translator::resolve(std::string_view setting, std::span<const std::string> preferred) const {
    if (setting != "auto") {
        return std::string(setting);
    }
    // First preferred language we have, exactly or through its parent.
    for (const std::string& want : preferred) {
        for (std::string_view code = want; !code.empty(); code = parent_code(code)) {
            if (const Catalog* c = find_catalog(code)) {
                return c->info().code;
            }
        }
    }
    return std::string(kBaseLanguage);
}

bool Translator::set_language(std::string_view code) {
    chain_.clear();
    for (std::string_view c = code; !c.empty(); c = parent_code(c)) {
        if (const Catalog* cat = find_catalog(c)) {
            chain_.push_back(cat);
        }
    }
    const bool matched = !chain_.empty();
    if (const Catalog* base = find_catalog(kBaseLanguage);
        base != nullptr && std::find(chain_.begin(), chain_.end(), base) == chain_.end()) {
        chain_.push_back(base);
    }
    ++generation_;
    if (!matched) {
        log::warn("i18n: language '{}' not available, using '{}'", code, kBaseLanguage);
    } else {
        log::info("i18n: language '{}'", active().code);
    }
    return matched;
}

const Entry* Translator::lookup(std::string_view key) const {
    for (const Catalog* c : chain_) {
        if (const Entry* e = find_in(c, key)) {
            if (c != chain_.front() && reported_missing_.insert(std::string(key)).second) {
                log::debug("i18n: '{}' missing in '{}', using '{}'", key, active().code, c->info().code);
            }
            return e;
        }
    }
    if (reported_missing_.insert(std::string(key)).second) {
        log::warn("i18n: missing text '{}'", key);
    }
    return nullptr;
}

std::string Translator::text(std::string_view key, std::span<const std::string> args) const {
    const Entry* e = lookup(key);
    // A missing text shows its key: visible, never blank.
    return e == nullptr ? std::string(key) : format_template(e->text(PluralCategory::Other), args);
}

std::string Translator::plural(std::string_view key, std::int64_t n, std::span<const std::string> args) const {
    const Entry* e = lookup(key);
    if (e == nullptr) {
        return std::string(key);
    }
    return format_template(e->text(plural_category(active().plural_rule, n)), args);
}

bool Translator::has(std::string_view key) const {
    return std::any_of(chain_.begin(), chain_.end(), [&](const Catalog* c) { return find_in(c, key) != nullptr; });
}

std::string Translator::format_int(std::int64_t value) const {
    return format_integer(active(), value);
}

const LanguageInfo& Translator::active() const {
    static const LanguageInfo kNone{};
    return chain_.empty() ? kNone : chain_.front()->info();
}

std::vector<const LanguageInfo*> Translator::available() const {
    std::vector<const LanguageInfo*> list;
    for (const auto& c : catalogs_) {
        list.push_back(&c->info());
    }
    std::sort(list.begin(), list.end(),
              [](const LanguageInfo* a, const LanguageInfo* b) { return a->native_name < b->native_name; });
    return list;
}

Translator& translator() {
    static Translator instance;
    return instance;
}

}  // namespace sc::i18n
