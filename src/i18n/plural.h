// CLDR plural categories and a table of plural rules. A language file names
// its rule by id, so adding a language needs no code as long as its rule is
// in the table.
#pragma once

#include <cstdint>
#include <optional>
#include <string_view>

namespace sc::i18n {

enum class PluralCategory : std::uint8_t { Zero, One, Two, Few, Many, Other };

enum class PluralRule : std::uint8_t {
    None,        // ja, zh, ko, vi, th, id...: always "other".
    One,         // en, de, nl, sv, it, es...: one if n == 1.
    OneUpToOne,  // fr, pt-BR, hi...: one if n is 0 or 1.
    EastSlavic,  // ru, uk, be: one, few, many.
    Polish,      // pl: one, few, many.
    Czech,       // cs, sk: one, few, other.
    Arabic,      // ar: zero, one, two, few, many, other.
};

[[nodiscard]] std::optional<PluralRule> plural_rule_from_id(std::string_view id);
[[nodiscard]] std::optional<PluralCategory> plural_category_from_name(std::string_view name);
[[nodiscard]] PluralCategory plural_category(PluralRule rule, std::int64_t n);

}  // namespace sc::i18n
