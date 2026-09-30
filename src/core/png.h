// A minimal PNG writer (phase 38): 8-bit RGB, no compression (stored
// deflate blocks), so it needs no library. Files are about 3 bytes per
// pixel, which is fine for screenshots kept in a temporary folder.
#pragma once

#include <cstdint>
#include <span>
#include <string>

namespace sc::png {

// `rgb` holds width * height * 3 bytes, rows from the top. Empty if the
// size is zero or does not match.
[[nodiscard]] std::string encode_rgb(std::span<const std::uint8_t> rgb, std::uint32_t width, std::uint32_t height);

}  // namespace sc::png
