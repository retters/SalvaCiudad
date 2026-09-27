#include <doctest.h>

#include "core/text.h"

using namespace sc;

TEST_SUITE("text") {
    TEST_CASE("valid and invalid UTF-8") {
        CHECK(text::is_valid_utf8(""));
        CHECK(text::is_valid_utf8("hola"));
        CHECK(text::is_valid_utf8("año, ñandú, 城市, 🏰"));
        CHECK_FALSE(text::is_valid_utf8("\xC3"));              // Truncated.
        CHECK_FALSE(text::is_valid_utf8("\xC0\xAF"));          // Overlong.
        CHECK_FALSE(text::is_valid_utf8("\xED\xA0\x80"));      // Surrogate.
        CHECK_FALSE(text::is_valid_utf8("\xF4\x90\x80\x80"));  // Above U+10FFFF.
        CHECK_FALSE(text::is_valid_utf8("\xFF"));
    }

    TEST_CASE("safe display text") {
        CHECK(text::is_safe_display_text("Monitor Dell 27\"", 64));
        CHECK(text::is_safe_display_text("Pantalla ñ", 64));
        CHECK_FALSE(text::is_safe_display_text("line\nbreak", 64));
        CHECK_FALSE(text::is_safe_display_text("tab\there", 64));
        CHECK_FALSE(text::is_safe_display_text("del\x7F", 64));
        CHECK_FALSE(text::is_safe_display_text("c1\xC2\x85", 64));
        CHECK_FALSE(text::is_safe_display_text("abcdef", 5));
        CHECK_FALSE(text::is_safe_display_text("\xC3", 64));
    }

    TEST_CASE("language settings") {
        CHECK(text::is_valid_language_setting("auto"));
        CHECK(text::is_valid_language_setting("es"));
        CHECK(text::is_valid_language_setting("es-MX"));
        CHECK(text::is_valid_language_setting("zh-Hant-TW"));
        CHECK(text::is_valid_language_setting("es-419"));
        CHECK_FALSE(text::is_valid_language_setting(""));
        CHECK_FALSE(text::is_valid_language_setting("e"));
        CHECK_FALSE(text::is_valid_language_setting("español"));
        CHECK_FALSE(text::is_valid_language_setting("es-"));
        CHECK_FALSE(text::is_valid_language_setting("es_MX"));
        CHECK_FALSE(text::is_valid_language_setting("../es"));
        CHECK_FALSE(text::is_valid_language_setting("es-a-b-c-d"));
    }

    TEST_CASE("paths round-trip through UTF-8") {
        const std::string name = "partidas/Año nuevo ñandú 城市.sav";
        const auto path = text::path_from_utf8(name);
        CHECK_FALSE(path.empty());
        CHECK(text::path_to_utf8(path) == text::path_to_utf8(text::path_from_utf8(name)));
        CHECK(text::path_to_utf8(path.filename()) == "Año nuevo ñandú 城市.sav");
        CHECK(text::path_from_utf8("\xC3").empty());
    }
}
