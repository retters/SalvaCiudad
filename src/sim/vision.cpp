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

void Vision::add_group(std::uint8_t group) {
    if (side_ <= 0 || group >= kVisionGroups || used(group)) {
        return;
    }
    groups_ = static_cast<std::uint16_t>(groups_ | (1u << group));
    explored_[group].reset(side_);
    count_[group] = 0;
    sum_[group] = 0;
    ghosts_[group].clear();
}

bool Vision::explored_at(std::uint8_t group, std::int32_t x, std::int32_t z) const {
    if (!used(group) || x < 0 || z < 0) {
        return false;
    }
    if (all_explored_) {
        return x / kFogCell < side_ && z / kFogCell < side_;
    }
    return explored_[group].get(x / kFogCell, z / kFogCell);
}

bool Vision::explored_rect(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (!used(group) || w <= 0 || d <= 0 || x < 0 || z < 0) {
        return false;
    }
    if (all_explored_) {
        return (x + w - 1) / kFogCell < side_ && (z + d - 1) / kFogCell < side_;
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

void Vision::reveal(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t radius, bool sight) {
    if (!used(group)) {
        return;
    }
    FogGrid& grid = explored_[group];
    FogGrid* seen = sight && !sight_[group].empty() ? &sight_[group] : nullptr;
    std::uint32_t& count = count_[group];
    std::uint64_t& sum = sum_[group];
    for_each_disc_row(side_, x, z, radius, [&](std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
        grid.set_span(cz, cx0, cx1, [&](std::size_t index) {
            ++count;
            sum += fog_cell_mix(index);
        });
        if (seen != nullptr) {
            seen->set_span(cz, cx0, cx1);
        }
    });
}

void Vision::begin_sight() {
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (!used(g)) {
            continue;
        }
        if (sight_[g].side() != side_) {
            sight_[g].reset(side_);
        } else {
            sight_[g].clear_all();
        }
    }
}

bool Vision::sees(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (!used(group) || w <= 0 || d <= 0) {
        return false;
    }
    const FogGrid& grid = sight_[group];
    for (std::int32_t cz = std::max(0, z) / kFogCell; cz <= std::max(0, z + d - 1) / kFogCell; ++cz) {
        for (std::int32_t cx = std::max(0, x) / kFogCell; cx <= std::max(0, x + w - 1) / kFogCell; ++cx) {
            if (grid.get(cx, cz)) {
                return true;
            }
        }
    }
    return false;
}

void Vision::remember(std::uint8_t group, const BuildingGhost& ghost) {
    if (!used(group)) {
        return;
    }
    std::vector<BuildingGhost>& list = ghosts_[group];
    const auto it = std::lower_bound(list.begin(), list.end(), ghost.id.index,
                                     [](const BuildingGhost& g, std::uint32_t index) { return g.id.index < index; });
    if (it != list.end() && it->id.index == ghost.id.index) {
        if (*it != ghost) {
            *it = ghost;
            ++ghost_revision_;
        }
        return;
    }
    list.insert(it, ghost);
    ++ghost_revision_;
}

void Vision::forget(std::uint8_t group, EntityId id) {
    if (!used(group)) {
        return;
    }
    std::vector<BuildingGhost>& list = ghosts_[group];
    const auto it = std::lower_bound(list.begin(), list.end(), id.index,
                                     [](const BuildingGhost& g, std::uint32_t index) { return g.id.index < index; });
    if (it != list.end() && it->id == id) {
        list.erase(it);
        ++ghost_revision_;
    }
}

void Vision::write_summary(BinaryWriter& w) const {
    w.u16(groups_);
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (!used(g)) {
            continue;
        }
        w.u32(count_[g]);
        w.u64(sum_[g]);
        w.u32(static_cast<std::uint32_t>(ghosts_[g].size()));
        for (const BuildingGhost& h : ghosts_[g]) {
            w.u32(h.id.index);
            w.u32(h.id.generation);
            w.u16(h.def);
            w.u8(h.owner);
            w.u8(h.rotation);
            w.u8(h.level);
            w.u8(h.burning ? 1 : 0);
            w.i32(h.x);
            w.i32(h.z);
            w.u16(static_cast<std::uint16_t>(h.progress));
            w.u16(static_cast<std::uint16_t>(h.burned));
        }
    }
}

bool Vision::read_summary(BinaryReader& r, std::size_t buildings, std::uint8_t players, std::int32_t map_size,
                          VisionSummary& out) {
    VisionSummary s;
    if (!r.u16(s.groups) || (s.groups >> kVisionGroups) != 0) {
        r.fail();
        return false;
    }
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (((s.groups >> g) & 1u) == 0) {
            continue;
        }
        std::uint32_t n = 0;
        if (!r.u32(s.counts[g]) || !r.u64(s.sums[g]) || !r.count(1u << 20, 26, n)) {
            r.fail();
            return false;
        }
        s.ghosts[g].resize(n);
        for (std::size_t k = 0; k < n; ++k) {
            BuildingGhost& h = s.ghosts[g][k];
            std::uint8_t burning = 0;
            std::uint16_t progress = 0, burned = 0;
            if (!r.u32(h.id.index) || !r.u32(h.id.generation) || !r.u16(h.def) || !r.u8(h.owner) || !r.u8(h.rotation) ||
                !r.u8(h.level) || !r.u8(burning) || !r.i32(h.x) || !r.i32(h.z) || !r.u16(progress) || !r.u16(burned) ||
                h.def >= buildings || h.owner >= players || h.rotation > 3 || burning > 1 || h.x < 0 || h.z < 0 ||
                h.x >= map_size || h.z >= map_size || progress > 1000 || burned > 1000 ||
                (k > 0 && h.id.index <= s.ghosts[g][k - 1].id.index)) {
                r.fail();
                return false;
            }
            h.burning = burning != 0;
            h.progress = static_cast<std::int16_t>(progress);
            h.burned = static_cast<std::int16_t>(burned);
        }
    }
    out = std::move(s);
    return true;
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

bool Vision::read(BinaryReader& r, std::int32_t map_size, bool expect_active, const VisionSummary& summary,
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
    if (summary.groups != v.groups_) {
        r.fail();
        return false;
    }
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (!v.used(g)) {
            continue;
        }
        if (summary.counts[g] != v.count_[g] || summary.sums[g] != v.sum_[g]) {
            r.fail();
            return false;
        }
        v.ghosts_[g] = summary.ghosts[g];
    }
    out = std::move(v);
    ++out.ghost_revision_;
    return true;
}

}  // namespace sc::sim
