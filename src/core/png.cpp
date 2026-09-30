#include "core/png.h"

#include <algorithm>
#include <array>

namespace sc::png {

namespace {

const std::array<std::uint32_t, 256>& crc_table() {
    static const std::array<std::uint32_t, 256> table = [] {
        std::array<std::uint32_t, 256> t{};
        for (std::uint32_t n = 0; n < 256; ++n) {
            std::uint32_t c = n;
            for (int k = 0; k < 8; ++k) {
                c = (c & 1u) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            }
            t[n] = c;
        }
        return t;
    }();
    return table;
}

void put_u32(std::string& out, std::uint32_t v) {
    out += static_cast<char>((v >> 24) & 0xFFu);
    out += static_cast<char>((v >> 16) & 0xFFu);
    out += static_cast<char>((v >> 8) & 0xFFu);
    out += static_cast<char>(v & 0xFFu);
}

// A chunk: length, type, data and the CRC of type and data.
void chunk(std::string& out, const char (&type)[5], const std::string& data) {
    put_u32(out, static_cast<std::uint32_t>(data.size()));
    const std::size_t start = out.size();
    out.append(type, 4);
    out += data;
    std::uint32_t c = 0xFFFFFFFFu;
    for (std::size_t i = start; i < out.size(); ++i) {
        c = crc_table()[(c ^ static_cast<std::uint8_t>(out[i])) & 0xFFu] ^ (c >> 8);
    }
    put_u32(out, c ^ 0xFFFFFFFFu);
}

}  // namespace

std::string encode_rgb(std::span<const std::uint8_t> rgb, std::uint32_t width, std::uint32_t height) {
    const std::uint64_t row = static_cast<std::uint64_t>(width) * 3u;
    if (width == 0 || height == 0 || width > 65535 || height > 65535 || rgb.size() != row * height) {
        return {};
    }
    // The image data: each row starts with filter type 0 (none).
    std::string raw;
    raw.reserve(static_cast<std::size_t>((row + 1) * height));
    for (std::uint32_t y = 0; y < height; ++y) {
        raw += '\0';
        raw.append(reinterpret_cast<const char*>(rgb.data() + y * row), static_cast<std::size_t>(row));
    }
    // zlib: header, stored blocks of up to 65535 bytes, Adler-32.
    std::string z;
    z.reserve(raw.size() + raw.size() / 65535 * 5 + 16);
    z += '\x78';
    z += '\x01';
    std::size_t pos = 0;
    do {
        const std::size_t n = std::min<std::size_t>(65535, raw.size() - pos);
        const bool last = pos + n == raw.size();
        z += static_cast<char>(last ? 1 : 0);
        z += static_cast<char>(n & 0xFFu);
        z += static_cast<char>((n >> 8) & 0xFFu);
        z += static_cast<char>(~n & 0xFFu);
        z += static_cast<char>((~n >> 8) & 0xFFu);
        z.append(raw, pos, n);
        pos += n;
    } while (pos < raw.size());
    std::uint32_t a = 1;
    std::uint32_t b = 0;
    for (const char ch : raw) {
        a = (a + static_cast<std::uint8_t>(ch)) % 65521u;
        b = (b + a) % 65521u;
    }
    put_u32(z, (b << 16) | a);

    std::string out = "\x89PNG\r\n\x1a\n";
    std::string header;
    put_u32(header, width);
    put_u32(header, height);
    header += '\x08';  // 8 bits per channel.
    header += '\x02';  // RGB.
    header += '\0';    // Deflate.
    header += '\0';    // Adaptive filtering.
    header += '\0';    // Not interlaced.
    chunk(out, "IHDR", header);
    chunk(out, "IDAT", z);
    chunk(out, "IEND", {});
    return out;
}

}  // namespace sc::png
