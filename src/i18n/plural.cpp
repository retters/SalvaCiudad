#include "i18n/plural.h"

namespace sc::i18n {

std::optional<PluralRule> plural_rule_from_id(std::string_view id) {
    if (id == "none") return PluralRule::None;
    if (id == "one") return PluralRule::One;
    if (id == "oneUpToOne") return PluralRule::OneUpToOne;
    if (id == "eastSlavic") return PluralRule::EastSlavic;
    if (id == "polish") return PluralRule::Polish;
    if (id == "czech") return PluralRule::Czech;
    if (id == "arabic") return PluralRule::Arabic;
    return std::nullopt;
}

std::optional<PluralCategory> plural_category_from_name(std::string_view name) {
    if (name == "zero") return PluralCategory::Zero;
    if (name == "one") return PluralCategory::One;
    if (name == "two") return PluralCategory::Two;
    if (name == "few") return PluralCategory::Few;
    if (name == "many") return PluralCategory::Many;
    if (name == "other") return PluralCategory::Other;
    return std::nullopt;
}

PluralCategory plural_category(PluralRule rule, std::int64_t n) {
    // Counts in the game are never negative; treat them by magnitude anyway.
    const std::uint64_t a = n < 0 ? 0 - static_cast<std::uint64_t>(n) : static_cast<std::uint64_t>(n);
    const std::uint64_t mod10 = a % 10;
    const std::uint64_t mod100 = a % 100;
    switch (rule) {
        case PluralRule::None:
            return PluralCategory::Other;
        case PluralRule::One:
            return a == 1 ? PluralCategory::One : PluralCategory::Other;
        case PluralRule::OneUpToOne:
            return a <= 1 ? PluralCategory::One : PluralCategory::Other;
        case PluralRule::EastSlavic:
            if (mod10 == 1 && mod100 != 11) return PluralCategory::One;
            if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return PluralCategory::Few;
            return PluralCategory::Many;
        case PluralRule::Polish:
            if (a == 1) return PluralCategory::One;
            if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return PluralCategory::Few;
            return PluralCategory::Many;
        case PluralRule::Czech:
            if (a == 1) return PluralCategory::One;
            if (a >= 2 && a <= 4) return PluralCategory::Few;
            return PluralCategory::Other;
        case PluralRule::Arabic:
            if (a == 0) return PluralCategory::Zero;
            if (a == 1) return PluralCategory::One;
            if (a == 2) return PluralCategory::Two;
            if (mod100 >= 3 && mod100 <= 10) return PluralCategory::Few;
            if (mod100 >= 11 && mod100 <= 99) return PluralCategory::Many;
            return PluralCategory::Other;
    }
    return PluralCategory::Other;
}

}  // namespace sc::i18n
