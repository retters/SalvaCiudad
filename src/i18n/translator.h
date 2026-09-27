// Runtime text lookup: the code asks for a key and gets the text in the
// active language, falling back es-MX -> es -> en. Languages are discovered
// from data/lang at startup, so adding one needs no code or rebuild.
#pragma once

#include <concepts>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_set>
#include <vector>

#include "i18n/catalog.h"

namespace sc::i18n {

inline constexpr std::string_view kBaseLanguage = "en";

// Replaces {0}, {1}... (optionally {0:name}, where the name only documents
// the placeholder for translators) with `args`. "{{" and "}}" are literal
// braces. Unknown or malformed placeholders are kept as written.
[[nodiscard]] std::string format_template(std::string_view tmpl, std::span<const std::string> args);

// Groups digits with the separators of `info`.
[[nodiscard]] std::string format_integer(const LanguageInfo& info, std::int64_t value);

class Translator {
public:
    // Loads the built-in base language and every *.json in `dir`. Invalid
    // files are skipped and logged. Returns the number of files skipped.
    int load(const std::filesystem::path& dir, std::string_view builtin_base_json);

    // Adds one language from memory (used by `load` and by the tests).
    bool add_language(std::string_view json_text, std::string_view origin_for_log);

    // Chooses a language code for a setting ("auto" or a code) and the
    // user's preferred UI languages (for example {"es-MX", "en-US"}).
    [[nodiscard]] std::string resolve(std::string_view setting, std::span<const std::string> preferred) const;

    // Activates `code` (or its closest available parent). Returns false if
    // nothing matched and the base language is used.
    bool set_language(std::string_view code);

    [[nodiscard]] std::string text(std::string_view key, std::span<const std::string> args = {}) const;
    [[nodiscard]] std::string plural(std::string_view key, std::int64_t n, std::span<const std::string> args) const;
    [[nodiscard]] bool has(std::string_view key) const;

    [[nodiscard]] std::string format_int(std::int64_t value) const;

    [[nodiscard]] const LanguageInfo& active() const;
    [[nodiscard]] std::vector<const LanguageInfo*> available() const;  // Sorted by name.
    // Changes every time the active language changes, so the UI can
    // refresh cached text.
    [[nodiscard]] std::uint64_t generation() const { return generation_; }

private:
    [[nodiscard]] const Catalog* find_catalog(std::string_view code) const;
    [[nodiscard]] const Entry* lookup(std::string_view key) const;

    std::vector<std::unique_ptr<Catalog>> catalogs_;
    std::vector<const Catalog*> chain_;  // Active language first, base last.
    std::uint64_t generation_ = 0;
    mutable std::unordered_set<std::string> reported_missing_;
};

// The game's translator, used by the UI.
Translator& translator();

namespace detail {
inline std::string to_arg(const std::string& s) { return s; }
inline std::string to_arg(std::string_view s) { return std::string(s); }
inline std::string to_arg(const char* s) { return s; }
template <std::integral T>
std::string to_arg(T v) {
    return translator().format_int(static_cast<std::int64_t>(v));
}
}  // namespace detail

// tr("menu.main.quit"), tr("menu.main.version", version_text)...
template <typename... Args>
[[nodiscard]] std::string tr(std::string_view key, Args&&... args) {
    if constexpr (sizeof...(Args) == 0) {
        return translator().text(key);
    } else {
        const std::string list[] = {detail::to_arg(std::forward<Args>(args))...};
        return translator().text(key, list);
    }
}

// Plural form chosen by `n`; {0} is n formatted, then the other arguments.
template <typename... Args>
[[nodiscard]] std::string tr_n(std::string_view key, std::int64_t n, Args&&... args) {
    const std::string list[] = {translator().format_int(n), detail::to_arg(std::forward<Args>(args))...};
    return translator().plural(key, n, list);
}

}  // namespace sc::i18n
