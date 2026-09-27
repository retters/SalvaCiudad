// Text helpers shared by the whole engine: UTF-8 validation and conversion
// between UTF-8 strings and filesystem paths.
#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

namespace sc::text {

// True if `s` is well-formed UTF-8 (no overlong forms, no surrogates, no
// code points above U+10FFFF).
[[nodiscard]] bool is_valid_utf8(std::string_view s);

// Decodes the code point at byte `i` and advances `i` past it. Malformed
// bytes decode as U+FFFD, one byte at a time. `i` must be < s.size().
[[nodiscard]] std::uint32_t next_codepoint(std::string_view s, std::size_t& i);

// True if `s` is valid UTF-8, at most `max_bytes` long and has no control
// characters (C0, DEL or C1). Used for any user-visible text read from files.
[[nodiscard]] bool is_safe_display_text(std::string_view s, std::size_t max_bytes);

// True for "auto" or a simple BCP 47 tag such as "es", "es-MX" or "zh-Hant":
// a 2-3 letter primary subtag followed by up to three 2-8 character
// alphanumeric subtags.
[[nodiscard]] bool is_valid_language_setting(std::string_view s);

// Returns an empty path if `utf8` is not valid UTF-8.
[[nodiscard]] std::filesystem::path path_from_utf8(std::string_view utf8);
[[nodiscard]] std::string path_to_utf8(const std::filesystem::path& path);

}  // namespace sc::text
