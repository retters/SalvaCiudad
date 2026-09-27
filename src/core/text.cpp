#include "core/text.h"

#include <cstdint>

#ifdef _WIN32
#include <windows.h>
#endif

namespace sc::text {

namespace {

bool is_ascii_alpha(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

bool is_ascii_alnum(char c) {
    return is_ascii_alpha(c) || (c >= '0' && c <= '9');
}

// Decodes one code point starting at `s[i]`. Returns the number of bytes
// consumed, or 0 if the sequence is malformed.
std::size_t decode_utf8(std::string_view s, std::size_t i, std::uint32_t& cp) {
    const auto b0 = static_cast<std::uint8_t>(s[i]);
    std::size_t len = 0;
    std::uint32_t min_cp = 0;
    if (b0 < 0x80) {
        cp = b0;
        return 1;
    }
    if ((b0 & 0xE0) == 0xC0) {
        len = 2;
        min_cp = 0x80;
        cp = b0 & 0x1Fu;
    } else if ((b0 & 0xF0) == 0xE0) {
        len = 3;
        min_cp = 0x800;
        cp = b0 & 0x0Fu;
    } else if ((b0 & 0xF8) == 0xF0) {
        len = 4;
        min_cp = 0x10000;
        cp = b0 & 0x07u;
    } else {
        return 0;
    }
    if (s.size() - i < len) {
        return 0;
    }
    for (std::size_t k = 1; k < len; ++k) {
        const auto b = static_cast<std::uint8_t>(s[i + k]);
        if ((b & 0xC0) != 0x80) {
            return 0;
        }
        cp = (cp << 6) | (b & 0x3Fu);
    }
    if (cp < min_cp || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) {
        return 0;
    }
    return len;
}

}  // namespace

bool is_valid_utf8(std::string_view s) {
    std::size_t i = 0;
    while (i < s.size()) {
        std::uint32_t cp = 0;
        const std::size_t len = decode_utf8(s, i, cp);
        if (len == 0) {
            return false;
        }
        i += len;
    }
    return true;
}

std::uint32_t next_codepoint(std::string_view s, std::size_t& i) {
    std::uint32_t cp = 0;
    const std::size_t len = decode_utf8(s, i, cp);
    if (len == 0) {
        ++i;
        return 0xFFFD;
    }
    i += len;
    return cp;
}

bool is_safe_display_text(std::string_view s, std::size_t max_bytes) {
    if (s.size() > max_bytes) {
        return false;
    }
    std::size_t i = 0;
    while (i < s.size()) {
        std::uint32_t cp = 0;
        const std::size_t len = decode_utf8(s, i, cp);
        if (len == 0) {
            return false;
        }
        if (cp < 0x20 || cp == 0x7F || (cp >= 0x80 && cp <= 0x9F)) {
            return false;
        }
        i += len;
    }
    return true;
}

bool is_valid_language_setting(std::string_view s) {
    if (s == "auto") {
        return true;
    }
    std::size_t i = 0;
    std::size_t subtag_index = 0;
    while (true) {
        const std::size_t start = i;
        while (i < s.size() && s[i] != '-') {
            ++i;
        }
        const std::string_view subtag = s.substr(start, i - start);
        if (subtag_index == 0) {
            if (subtag.size() < 2 || subtag.size() > 3) {
                return false;
            }
            for (const char c : subtag) {
                if (!is_ascii_alpha(c)) {
                    return false;
                }
            }
        } else {
            if (subtag.size() < 2 || subtag.size() > 8 || subtag_index > 3) {
                return false;
            }
            for (const char c : subtag) {
                if (!is_ascii_alnum(c)) {
                    return false;
                }
            }
        }
        if (i == s.size()) {
            return true;
        }
        ++i;  // Skip '-'.
        ++subtag_index;
    }
}

std::filesystem::path path_from_utf8(std::string_view utf8) {
    // The standard library reports malformed input with an exception, which
    // this project compiles out, so reject it before converting.
    if (!is_valid_utf8(utf8)) {
        return {};
    }
    const std::u8string u8(reinterpret_cast<const char8_t*>(utf8.data()), utf8.size());
    return std::filesystem::path(u8);
}

std::string path_to_utf8(const std::filesystem::path& path) {
#ifdef _WIN32
    // path::u8string() fails on unpaired surrogates, which Windows file names
    // may contain; WideCharToMultiByte replaces them with U+FFFD instead.
    const std::wstring& wide = path.native();
    if (wide.empty() || wide.size() > static_cast<std::size_t>(INT32_MAX)) {
        return {};
    }
    const int wide_len = static_cast<int>(wide.size());
    const int len = WideCharToMultiByte(CP_UTF8, 0, wide.data(), wide_len, nullptr, 0, nullptr, nullptr);
    if (len <= 0) {
        return {};
    }
    std::string out(static_cast<std::size_t>(len), '\0');
    if (WideCharToMultiByte(CP_UTF8, 0, wide.data(), wide_len, out.data(), len, nullptr, nullptr) != len) {
        return {};
    }
    return out;
#else
    return path.native();
#endif
}

}  // namespace sc::text
