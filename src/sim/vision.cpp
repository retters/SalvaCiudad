#include "sim/vision.h"

#include <algorithm>

namespace sc::sim {

void FogGrid::reset(std::int32_t side) {
    side_ = std::max(0, side);
    const std::size_t cells = static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_);
    words_.assign((cells + 63) / 64, 0);
}

void FogGrid::clear_all() {
    std::fill(words_.begin(), words_.end(), 0ull);
}

std::uint64_t fog_cell_mix(std::size_t index) {
    std::uint64_t x = static_cast<std::uint64_t>(index) + 0x9E3779B97F4A7C15ull;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
    return x ^ (x >> 31);
}

void Vision::clear() {
    *this = Vision{};
}

void Vision::reset(std::int32_t map_size, std::uint16_t groups) {
    clear();
    side_ = fog_side(map_size);
    groups_ = side_ > 0 ? static_cast<std::uint16_t>(groups & ((1u << kVisionGroups) - 1)) : 0;
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (used(g)) {
            explored_[g].reset(side_);
        }
    }
    if (groups_ == 0) {
        side_ = 0;
    }
}

bool Vision::explored_at(std::uint8_t group, std::int32_t x, std::int32_t z) const {
    if (!used(group) || x < 0 || z < 0) {
        return false;
    }
    return explored_[group].get(x / kFogCell, z / kFogCell);
}

bool Vision::explored_rect(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (!used(group) || w <= 0 || d <= 0 || x < 0 || z < 0) {
        return false;
    }
    const FogGrid& grid = explored_[group];
    for (std::int32_t cz = z / kFogCell; cz <= (z + d - 1) / kFogCell; ++cz) {
        for (std::int32_t cx = x / kFogCell; cx <= (x + w - 1) / kFogCell; ++cx) {
            if (!grid.get(cx, cz)) {
                return false;
            }
        }
    }
    return true;
}

void Vision::reveal(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t radius) {
    if (!used(group)) {
        return;
    }
    FogGrid& grid = explored_[group];
    std::uint32_t& count = count_[group];
    std::uint64_t& sum = sum_[group];
    for_each_disc_row(side_, x, z, radius, [&](std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
        grid.set_span(cz, cx0, cx1, [&](std::size_t index) {
            ++count;
            sum += fog_cell_mix(index);
        });
    });
}

void Vision::write_summary(BinaryWriter& w) const {
    w.u16(groups_);
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (used(g)) {
            w.u32(count_[g]);
            w.u64(sum_[g]);
        }
    }
}

void Vision::write(BinaryWriter& w) const {
    w.i32(side_);
    w.u16(groups_);
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (!used(g)) {
            continue;
        }
        for (const std::uint64_t word : explored_[g].words()) {
            w.u64(word);
        }
    }
}

bool Vision::read(BinaryReader& r, std::int32_t map_size, bool expect_active, std::span<const std::uint8_t> summary,
                  Vision& out) {
    std::int32_t side = 0;
    std::uint16_t groups = 0;
    if (!r.i32(side) || !r.u16(groups) || (groups >> kVisionGroups) != 0) {
        r.fail();
        return false;
    }
    Vision v;
    if (!expect_active) {
        if (side != 0 || groups != 0) {
            r.fail();
            return false;
        }
    } else {
        if (side != fog_side(map_size) || side <= 0 || groups == 0) {
            r.fail();
            return false;
        }
        v.reset(map_size, groups);
        for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
            if (!v.used(g)) {
                continue;
            }
            std::vector<std::uint64_t>& words = v.explored_[g].words();
            if (r.remaining() / 8 < words.size()) {
                r.fail();
                return false;
            }
            for (std::uint64_t& word : words) {
                if (!r.u64(word)) {
                    return false;
                }
            }
            // No bits past the last cell.
            const std::size_t cells = static_cast<std::size_t>(side) * static_cast<std::size_t>(side);
            if ((cells & 63u) != 0 && (words.back() >> (cells & 63u)) != 0) {
                r.fail();
                return false;
            }
            std::uint32_t count = 0;
            std::uint64_t sum = 0;
            for (std::size_t k = 0; k < words.size(); ++k) {
                std::uint64_t bits = words[k];
                count += static_cast<std::uint32_t>(std::popcount(bits));
                while (bits != 0) {
                    sum += fog_cell_mix((k << 6) | static_cast<std::size_t>(std::countr_zero(bits)));
                    bits &= bits - 1;
                }
            }
            v.count_[g] = count;
            v.sum_[g] = sum;
        }
    }
    // The saved summary must say the same.
    BinaryWriter mine;
    v.write_summary(mine);
    if (!std::equal(mine.bytes().begin(), mine.bytes().end(), summary.begin(), summary.end())) {
        r.fail();
        return false;
    }
    out = std::move(v);
    return true;
}

}  // namespace sc::sim
