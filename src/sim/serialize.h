// Explicit little-endian binary encoding for simulation state, commands and
// replays. The same bytes on every platform; readers treat their input as
// untrusted and fail (never crash) on truncated or out-of-range data.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "sim/fixed.h"

namespace sc::sim {

class BinaryWriter {
public:
    void u8(std::uint8_t v) { bytes_.push_back(v); }
    void u16(std::uint16_t v);
    void u32(std::uint32_t v);
    void u64(std::uint64_t v);
    void i32(std::int32_t v) { u32(static_cast<std::uint32_t>(v)); }
    void i64(std::int64_t v) { u64(static_cast<std::uint64_t>(v)); }
    void fixed(Fixed v) { i32(v.raw()); }
    void vec2(FixedVec2 v) {
        fixed(v.x);
        fixed(v.z);
    }
    void raw(std::span<const std::uint8_t> data) { bytes_.insert(bytes_.end(), data.begin(), data.end()); }
    // Phase 144: room for `more` bytes, so a large save is not copied over
    // and over as it grows.
    void reserve_more(std::size_t more) { bytes_.reserve(bytes_.size() + more); }
    void string(std::string_view s);

    [[nodiscard]] const std::vector<std::uint8_t>& bytes() const { return bytes_; }
    [[nodiscard]] std::vector<std::uint8_t>& bytes() { return bytes_; }

private:
    std::vector<std::uint8_t> bytes_;
};

class BinaryReader {
public:
    explicit BinaryReader(std::span<const std::uint8_t> data) : data_(data) {}

    // Each returns false (and leaves the reader failed) if the data runs out.
    bool u8(std::uint8_t& v);
    bool u16(std::uint16_t& v);
    bool u32(std::uint32_t& v);
    bool u64(std::uint64_t& v);
    bool i32(std::int32_t& v);
    bool i64(std::int64_t& v);
    bool fixed(Fixed& v);
    bool vec2(FixedVec2& v);
    bool bytes(std::size_t count, std::span<const std::uint8_t>& out);
    // A length-prefixed string of at most `max_bytes`.
    bool string(std::size_t max_bytes, std::string& out);
    // A count that must not exceed `max` (and must fit in what is left if
    // each item takes at least `min_item_bytes`).
    bool count(std::uint32_t max, std::size_t min_item_bytes, std::uint32_t& out);

    [[nodiscard]] bool ok() const { return ok_; }
    [[nodiscard]] bool at_end() const { return ok_ && pos_ == data_.size(); }
    [[nodiscard]] std::size_t remaining() const { return data_.size() - pos_; }
    void fail() { ok_ = false; }

private:
    bool take(std::size_t n, const std::uint8_t*& p);

    std::span<const std::uint8_t> data_;
    std::size_t pos_ = 0;
    bool ok_ = true;
};

// FNV-1a, 64 bits: fast, stable and good enough to detect desyncs.
[[nodiscard]] std::uint64_t fnv1a64(std::span<const std::uint8_t> data, std::uint64_t seed = 0xcbf29ce484222325ull);

}  // namespace sc::sim
