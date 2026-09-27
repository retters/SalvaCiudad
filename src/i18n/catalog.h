// One language file: its metadata and its texts. Parsed without trusting the
// file (section 5.3 of the specification).
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>

#include "i18n/plural.h"

namespace sc::i18n {

namespace catalog_limits {
inline constexpr int kSchemaVersion = 1;
inline constexpr std::size_t kMaxFileBytes = 2u * 1024u * 1024u;
inline constexpr std::size_t kMaxEntries = 20000;
inline constexpr std::size_t kMaxKeyBytes = 128;
inline constexpr std::size_t kMaxTextBytes = 4096;
inline constexpr std::size_t kMaxNameBytes = 64;
inline constexpr std::size_t kMaxSeparatorBytes = 4;
}  // namespace catalog_limits

struct LanguageInfo {
    std::string code;         // BCP 47, for example "es" or "es-MX".
    std::string native_name;  // "Español", shown in the language list.
    PluralRule plural_rule = PluralRule::One;
    std::string decimal_separator = ".";
    std::string group_separator = ",";
    int minimum_grouping_digits = 1;  // 2: "1000" but "10 000".
};

// A text, or one text per plural category (Other is always present).
struct Entry {
    std::array<std::optional<std::string>, 6> forms;  // Indexed by PluralCategory.
    // The form for `c`, or "other" if the language file does not have it.
    [[nodiscard]] const std::string& text(PluralCategory c) const;
};

struct CatalogLoadResult {
    bool ok = false;           // False: the file is unusable (structure broken).
    std::string error;         // English, for the log.
    int ignored_entries = 0;   // Entries skipped as invalid.
};

class Catalog {
public:
    CatalogLoadResult load(std::string_view json_text);

    [[nodiscard]] const LanguageInfo& info() const { return info_; }
    [[nodiscard]] const Entry* find(std::string_view key) const;
    [[nodiscard]] std::size_t size() const { return entries_.size(); }
    [[nodiscard]] const std::unordered_map<std::string, Entry>& entries() const { return entries_; }

private:
    LanguageInfo info_;
    std::unordered_map<std::string, Entry> entries_;
};

// Keys are ASCII letters, digits, '_' and '.', like "menu.main.singlePlayer".
[[nodiscard]] bool is_valid_key(std::string_view key);

// Visible text: valid UTF-8 with no control characters except line breaks.
[[nodiscard]] bool is_valid_text(std::string_view text);

}  // namespace sc::i18n
