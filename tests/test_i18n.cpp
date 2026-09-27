#include <doctest.h>

#include <filesystem>
#include <fstream>
#include <regex>
#include <ostream>
#include <set>
#include <sstream>

#include "game/input_actions.h"
#include "i18n/catalog.h"
#include "i18n/translator.h"
#include "test_util.h"

using namespace sc;
using namespace sc::i18n;

namespace {

const std::filesystem::path kLangDir = std::filesystem::path(SC_SOURCE_DIR) / "data" / "lang";

std::string lang_file(std::string_view code, std::string_view strings, std::string_view rule = "one") {
    return std::string(R"({"schemaVersion": 1, "language": {"code": ")") + std::string(code) + R"(", "name": "N )" +
           std::string(code) + R"(", "pluralRule": ")" + std::string(rule) + R"("}, "strings": )" +
           std::string(strings) + "}";
}

std::set<std::string> keys_of(const Catalog& c) {
    std::set<std::string> keys;
    for (const auto& [k, v] : c.entries()) {
        keys.insert(k);
    }
    return keys;
}

Catalog load_real(std::string_view file) {
    Catalog c;
    const auto text = test::read_text(kLangDir / file);
    const auto r = c.load(text);
    REQUIRE(r.ok);
    CHECK(r.ignored_entries == 0);
    return c;
}

}  // namespace

TEST_SUITE("i18n") {
    TEST_CASE("plural rules") {
        CHECK(plural_category(PluralRule::One, 1) == PluralCategory::One);
        CHECK(plural_category(PluralRule::One, 0) == PluralCategory::Other);
        CHECK(plural_category(PluralRule::One, 21) == PluralCategory::Other);
        CHECK(plural_category(PluralRule::OneUpToOne, 0) == PluralCategory::One);
        CHECK(plural_category(PluralRule::None, 1) == PluralCategory::Other);
        CHECK(plural_category(PluralRule::EastSlavic, 21) == PluralCategory::One);
        CHECK(plural_category(PluralRule::EastSlavic, 11) == PluralCategory::Many);
        CHECK(plural_category(PluralRule::EastSlavic, 23) == PluralCategory::Few);
        CHECK(plural_category(PluralRule::EastSlavic, 13) == PluralCategory::Many);
        CHECK(plural_category(PluralRule::Polish, 1) == PluralCategory::One);
        CHECK(plural_category(PluralRule::Polish, 22) == PluralCategory::Few);
        CHECK(plural_category(PluralRule::Polish, 21) == PluralCategory::Many);
        CHECK(plural_category(PluralRule::Czech, 3) == PluralCategory::Few);
        CHECK(plural_category(PluralRule::Czech, 5) == PluralCategory::Other);
        CHECK(plural_category(PluralRule::Arabic, 0) == PluralCategory::Zero);
        CHECK(plural_category(PluralRule::Arabic, 2) == PluralCategory::Two);
        CHECK(plural_category(PluralRule::Arabic, 105) == PluralCategory::Few);
        CHECK(plural_category(PluralRule::Arabic, 111) == PluralCategory::Many);
        CHECK(plural_category(PluralRule::Arabic, 100) == PluralCategory::Other);
        CHECK_FALSE(plural_rule_from_id("klingon").has_value());
    }

    TEST_CASE("templates") {
        const std::vector<std::string> args = {"A", "B"};
        CHECK(format_template("{0} and {1}", args) == "A and B");
        CHECK(format_template("{1} before {0}", args) == "B before A");
        CHECK(format_template("{0:name} named", args) == "A named");
        CHECK(format_template("{{0}} literal", args) == "{0} literal");
        CHECK(format_template("{2} missing", args) == "{2} missing");
        CHECK(format_template("{x} {", args) == "{x} {");
        CHECK(format_template("", args).empty());
    }

    TEST_CASE("integer formatting") {
        LanguageInfo en;
        en.group_separator = ",";
        CHECK(format_integer(en, 0) == "0");
        CHECK(format_integer(en, 999) == "999");
        CHECK(format_integer(en, 1000) == "1,000");
        CHECK(format_integer(en, -1234567) == "-1,234,567");
        LanguageInfo es;
        es.group_separator = "\xC2\xA0";
        es.minimum_grouping_digits = 2;
        CHECK(format_integer(es, 1000) == "1000");
        CHECK(format_integer(es, 10000) == "10\xC2\xA0" "000");
        CHECK(format_integer(es, INT64_MIN).size() > 19);
    }

    TEST_CASE("catalog validation skips bad entries and rejects broken files") {
        Catalog c;
        auto r = c.load(lang_file("xx", R"({"ok.key": "Hi", "Bad Key": "x", "ctl.key": "a\u0007b",
            "nl.key": "line\nline", "plural.nootherkey": {"one": "x"}, "plural.good": {"one": "1", "other": "n"},
            "plural.badform": {"lots": "x", "other": "y"}, "num.key": 5})"));
        REQUIRE(r.ok);
        CHECK(r.ignored_entries == 5);
        CHECK(c.find("ok.key") != nullptr);
        CHECK(c.find("nl.key") != nullptr);
        CHECK(c.find("plural.good") != nullptr);

        CHECK_FALSE(c.load("{").ok);
        CHECK_FALSE(c.load(R"({"schemaVersion": 1, "strings": {}})").ok);
        CHECK_FALSE(c.load(lang_file("auto", "{}")).ok);
        CHECK_FALSE(c.load(lang_file("xx", "{}", "nope")).ok);
        CHECK_FALSE(c.load(lang_file("xx", "[]")).ok);
        CHECK_FALSE(c.load(R"({"schemaVersion": 9, "language": {"code": "xx", "name": "X", "pluralRule": "one"}, "strings": {}})").ok);
    }

    TEST_CASE("fallback chain, missing keys and resolution") {
        Translator t;
        (void)t.load(std::filesystem::path{}, lang_file("en", R"({"a": "A en", "b": "B en", "n": {"one": "{0} thing", "other": "{0} things"}})"));
        REQUIRE(t.add_language(lang_file("es", R"({"a": "A es", "n": {"one": "{0} cosa", "other": "{0} cosas"}})"), "es"));
        REQUIRE(t.add_language(lang_file("es-MX", R"({})"), "es-MX"));

        CHECK(t.set_language("es-MX"));
        CHECK(t.active().code == "es-MX");
        CHECK(t.text("a") == "A es");           // From es.
        CHECK(t.text("b") == "B en");           // From the base.
        CHECK(t.text("missing.key") == "missing.key");
        const std::vector<std::string> one = {"1"};
        const std::vector<std::string> two = {"2"};
        CHECK(t.plural("n", 1, one) == "1 cosa");
        CHECK(t.plural("n", 2, two) == "2 cosas");

        CHECK_FALSE(t.set_language("fr"));
        CHECK(t.text("a") == "A en");

        const std::vector<std::string> prefs = {"fr-FR", "es-AR", "en-US"};
        CHECK(t.resolve("auto", prefs) == "es");
        const std::vector<std::string> mx = {"es-MX"};
        CHECK(t.resolve("auto", mx) == "es-MX");
        CHECK(t.resolve("auto", {}) == "en");
        CHECK(t.resolve("es", prefs) == "es");
    }

    TEST_CASE("the shipped language files are valid and complete") {
        const Catalog en = load_real("en.json");
        const Catalog es = load_real("es.json");
        const Catalog es_mx = load_real("es-MX.json");
        CHECK(en.info().code == "en");
        CHECK(es.info().code == "es");
        CHECK(es_mx.info().code == "es-MX");

        const auto en_keys = keys_of(en);
        const auto es_keys = keys_of(es);
        for (const auto& k : en_keys) {
            CHECK_MESSAGE(es_keys.contains(k), "missing in es.json: " << k);
        }
        for (const auto& k : es_keys) {
            CHECK_MESSAGE(en_keys.contains(k), "missing in en.json: " << k);
        }
        // A variant only overrides what differs; it has no keys of its own.
        for (const auto& k : keys_of(es_mx)) {
            CHECK_MESSAGE(en_keys.contains(k), "unknown key in es-MX.json: " << k);
        }
    }

    TEST_CASE("every text key used in the code exists") {
        const Catalog en = load_real("en.json");
        const std::regex call(R"re(\btr(?:_n)?\(\s*"([a-zA-Z0-9_.]+)")re");
        int found = 0;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(std::filesystem::path(SC_SOURCE_DIR) / "src")) {
            if (entry.path().extension() != ".cpp" && entry.path().extension() != ".h") {
                continue;
            }
            const std::string code = test::read_text(entry.path());
            for (std::sregex_iterator it(code.begin(), code.end(), call), end; it != end; ++it) {
                const std::string key = (*it)[1].str();
                // Keys ending in '.' are prefixes completed at run time.
                if (key.back() == '.') {
                    continue;
                }
                ++found;
                CHECK_MESSAGE(en.find(key) != nullptr, "unknown key " << key << " in " << entry.path().filename().string());
            }
        }
        CHECK(found > 50);

        // Keys built at run time.
        for (const ActionInfo& info : action_table()) {
            CHECK_MESSAGE(en.find("action." + std::string(info.id)) != nullptr, info.id);
        }
        for (const char* tab : {"display", "graphics", "audio", "controls", "interface", "language", "game"}) {
            CHECK(en.find(std::string("settings.tab.") + tab) != nullptr);
        }
        for (const char* level : {"shadows", "drawDistance", "vegetation", "antialiasing"}) {
            for (int i = 0; i < 4; ++i) {
                CHECK(en.find(std::string("settings.graphics.") + level + ".level." + std::to_string(i)) != nullptr);
            }
            CHECK(en.find(std::string("settings.graphics.") + level + ".tooltip") != nullptr);
        }
        for (const char* v : {"master", "effects", "ambient", "music", "ui"}) {
            CHECK(en.find(std::string("settings.audio.") + v + ".tooltip") != nullptr);
        }
        for (const char* v : {"panSpeed", "rotateSpeed", "zoomSpeed"}) {
            CHECK(en.find(std::string("settings.controls.") + v + ".tooltip") != nullptr);
        }
    }
}

TEST_SUITE("i18n") {
    TEST_CASE("every key the player can bind has a readable name") {
        const std::string en = test::read_text(kLangDir / "en.json");
        REQUIRE(translator().load(kLangDir, en) == 0);
        for (const char* code : {"en", "es"}) {
            REQUIRE(translator().set_language(code));
            for (int k = 1; k < SDL_SCANCODE_COUNT; ++k) {
                const std::string name = key_display_name(static_cast<SDL_Scancode>(k));
                CHECK_FALSE_MESSAGE(name.starts_with("key."), "untranslated key name " << name);
            }
        }
        CHECK(key_display_name(SDL_SCANCODE_UP) == "Flecha arriba");
        (void)translator().set_language("en");
        CHECK(key_display_name(SDL_SCANCODE_UP) == "Up arrow");
    }
}
