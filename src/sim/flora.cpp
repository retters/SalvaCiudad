#include "sim/flora.h"

namespace sc::sim {

namespace {

constexpr SizeInfo kSizes[kTreeSizes] = {
    // Phase 54: the trunks keep further apart, for the wide crowns of the
    // low-poly trees.
    {"small", 100, 700, 450, 5},
    {"medium", 700, 1200, 950, 7},
    {"large", 1200, 2400, 1800, 10},
    {"huge", 2400, 4300, 3300, 16},
};

template <typename T>
int find_id(const std::vector<T>& list, std::string_view id) {
    for (std::size_t i = 0; i < list.size(); ++i) {
        if (list[i].id == id) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

}  // namespace

const SizeInfo& size_info(TreeSize size) {
    const auto i = static_cast<std::size_t>(size);
    return kSizes[i < kTreeSizes ? i : 0];
}

bool Flora::species_has_size(std::size_t s, TreeSize size) const {
    return s < species.size() && ((species[s].sizes >> static_cast<unsigned>(size)) & 1u) != 0;
}

TreeSize Flora::fit_size(std::size_t s, TreeSize wanted) const {
    const int w = static_cast<int>(wanted);
    for (int d = 0; d < static_cast<int>(kTreeSizes); ++d) {
        for (const int candidate : {w - d, w + d}) {
            if (candidate >= 0 && candidate < static_cast<int>(kTreeSizes) &&
                species_has_size(s, static_cast<TreeSize>(candidate))) {
                return static_cast<TreeSize>(candidate);
            }
        }
    }
    return TreeSize::Small;
}

int Flora::find_species(std::string_view id) const {
    return find_id(species, id);
}

int Flora::find_biome(std::string_view id) const {
    return find_id(biomes, id);
}

std::uint8_t pick_weighted(std::span<const Weighted> items, std::uint32_t roll16) {
    std::uint32_t total = 0;
    for (const Weighted& w : items) {
        total += w.weight;
    }
    if (items.empty()) {
        return 0;
    }
    if (total == 0) {
        return items.front().id;
    }
    std::uint32_t target = (roll16 & 0xFFFFu) * total >> 16;
    for (const Weighted& w : items) {
        if (target < w.weight) {
            return w.id;
        }
        target -= w.weight;
    }
    return items.back().id;
}

}  // namespace sc::sim
