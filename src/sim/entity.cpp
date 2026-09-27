#include "sim/entity.h"

#include <utility>

namespace sc::sim {

EntityId EntityRegistry::create() {
    std::uint32_t index = 0;
    if (!free_.empty()) {
        index = free_.back();
        free_.pop_back();
    } else {
        if (generations_.size() >= kMaxEntities) {
            return {};
        }
        index = static_cast<std::uint32_t>(generations_.size());
        generations_.push_back(0);
        alive_.push_back(0);
    }
    alive_[index] = 1;
    ++alive_count_;
    return {index, generations_[index]};
}

bool EntityRegistry::destroy(EntityId id) {
    if (!alive(id)) {
        return false;
    }
    alive_[id.index] = 0;
    ++generations_[id.index];  // Old ids to this slot stop matching.
    free_.push_back(id.index);
    --alive_count_;
    return true;
}

bool EntityRegistry::alive(EntityId id) const {
    return id.index < generations_.size() && alive_[id.index] != 0 && generations_[id.index] == id.generation;
}

bool EntityRegistry::restore(std::vector<std::uint32_t> generations, std::vector<std::uint8_t> alive,
                             std::vector<std::uint32_t> free) {
    if (generations.size() != alive.size() || generations.size() > kMaxEntities) {
        return false;
    }
    // Every free slot must be dead and listed once; every dead slot free.
    std::vector<std::uint8_t> seen(generations.size(), 0);
    for (const std::uint32_t f : free) {
        if (f >= generations.size() || alive[f] != 0 || seen[f] != 0) {
            return false;
        }
        seen[f] = 1;
    }
    std::uint32_t count = 0;
    for (std::size_t i = 0; i < alive.size(); ++i) {
        if (alive[i] > 1 || (alive[i] == 0 && seen[i] == 0)) {
            return false;
        }
        count += alive[i];
    }
    generations_ = std::move(generations);
    alive_ = std::move(alive);
    free_ = std::move(free);
    alive_count_ = count;
    return true;
}

}  // namespace sc::sim
