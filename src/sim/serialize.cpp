#include "sim/serialize.h"

namespace sc::sim {

void BinaryWriter::u16(std::uint16_t v) {
    u8(static_cast<std::uint8_t>(v));
    u8(static_cast<std::uint8_t>(v >> 8));
}

void BinaryWriter::u32(std::uint32_t v) {
    for (int i = 0; i < 4; ++i) {
        u8(static_cast<std::uint8_t>(v >> (8 * i)));
    }
}

void BinaryWriter::u64(std::uint64_t v) {
    for (int i = 0; i < 8; ++i) {
        u8(static_cast<std::uint8_t>(v >> (8 * i)));
    }
}

void BinaryWriter::string(std::string_view s) {
    u32(static_cast<std::uint32_t>(s.size()));
    bytes_.insert(bytes_.end(), s.begin(), s.end());
}

bool BinaryReader::take(std::size_t n, const std::uint8_t*& p) {
    if (!ok_ || n > data_.size() - pos_) {
        ok_ = false;
        return false;
    }
    p = data_.data() + pos_;
    pos_ += n;
    return true;
}

bool BinaryReader::u8(std::uint8_t& v) {
    const std::uint8_t* p = nullptr;
    if (!take(1, p)) {
        return false;
    }
    v = p[0];
    return true;
}

bool BinaryReader::u16(std::uint16_t& v) {
    const std::uint8_t* p = nullptr;
    if (!take(2, p)) {
        return false;
    }
    v = static_cast<std::uint16_t>(p[0] | (p[1] << 8));
    return true;
}

bool BinaryReader::u32(std::uint32_t& v) {
    const std::uint8_t* p = nullptr;
    if (!take(4, p)) {
        return false;
    }
    v = 0;
    for (int i = 3; i >= 0; --i) {
        v = (v << 8) | p[i];
    }
    return true;
}

bool BinaryReader::u64(std::uint64_t& v) {
    const std::uint8_t* p = nullptr;
    if (!take(8, p)) {
        return false;
    }
    v = 0;
    for (int i = 7; i >= 0; --i) {
        v = (v << 8) | p[i];
    }
    return true;
}

bool BinaryReader::i32(std::int32_t& v) {
    std::uint32_t u = 0;
    if (!u32(u)) {
        return false;
    }
    v = static_cast<std::int32_t>(u);
    return true;
}

bool BinaryReader::i64(std::int64_t& v) {
    std::uint64_t u = 0;
    if (!u64(u)) {
        return false;
    }
    v = static_cast<std::int64_t>(u);
    return true;
}

bool BinaryReader::fixed(Fixed& v) {
    std::int32_t raw = 0;
    if (!i32(raw)) {
        return false;
    }
    v = Fixed::from_raw(raw);
    return true;
}

bool BinaryReader::vec2(FixedVec2& v) {
    return fixed(v.x) && fixed(v.z);
}

bool BinaryReader::bytes(std::size_t count, std::span<const std::uint8_t>& out) {
    const std::uint8_t* p = nullptr;
    if (!take(count, p)) {
        return false;
    }
    out = {p, count};
    return true;
}

bool BinaryReader::string(std::size_t max_bytes, std::string& out) {
    std::uint32_t len = 0;
    if (!u32(len) || len > max_bytes) {
        ok_ = false;
        return false;
    }
    std::span<const std::uint8_t> s;
    if (!bytes(len, s)) {
        return false;
    }
    out.assign(reinterpret_cast<const char*>(s.data()), s.size());
    return true;
}

bool BinaryReader::count(std::uint32_t max, std::size_t min_item_bytes, std::uint32_t& out) {
    if (!u32(out)) {
        return false;
    }
    if (out > max || (min_item_bytes > 0 && out > remaining() / min_item_bytes)) {
        ok_ = false;
        return false;
    }
    return true;
}

std::uint64_t fnv1a64(std::span<const std::uint8_t> data, std::uint64_t seed) {
    std::uint64_t h = seed;
    for (const std::uint8_t b : data) {
        h ^= b;
        h *= 0x100000001b3ull;
    }
    return h;
}

}  // namespace sc::sim
