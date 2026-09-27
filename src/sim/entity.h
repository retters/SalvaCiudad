// Entities and their components. Identifiers are sequential slots with a
// generation, so a stale id never reaches a reused slot. Iteration order
// depends only on the order of operations, never on memory addresses or
// hashing (section 7.3).
#pragma once

#include <cstdint>
#include <limits>
#include <vector>

namespace sc::sim {

struct EntityId {
    std::uint32_t index = std::numeric_limits<std::uint32_t>::max();
    std::uint32_t generation = 0;

    [[nodiscard]] bool valid() const { return index != std::numeric_limits<std::uint32_t>::max(); }
    bool operator==(const EntityId&) const = default;
};

class EntityRegistry {
public:
    static constexpr std::uint32_t kMaxEntities = 1u << 22;  // About 4 million slots.

    // An invalid id when the registry is full.
    EntityId create();
    bool destroy(EntityId id);
    [[nodiscard]] bool alive(EntityId id) const;
    [[nodiscard]] std::uint32_t alive_count() const { return alive_count_; }
    [[nodiscard]] std::uint32_t slot_count() const { return static_cast<std::uint32_t>(generations_.size()); }

    // Raw state, for saving and loading.
    [[nodiscard]] const std::vector<std::uint32_t>& generations() const { return generations_; }
    [[nodiscard]] const std::vector<std::uint8_t>& alive_flags() const { return alive_; }
    [[nodiscard]] const std::vector<std::uint32_t>& free_slots() const { return free_; }
    // Rebuilds from saved state; returns false if it is inconsistent.
    bool restore(std::vector<std::uint32_t> generations, std::vector<std::uint8_t> alive, std::vector<std::uint32_t> free);

    bool operator==(const EntityRegistry&) const = default;

private:
    std::vector<std::uint32_t> generations_;
    std::vector<std::uint8_t> alive_;
    std::vector<std::uint32_t> free_;  // Reused last-in, first-out.
    std::uint32_t alive_count_ = 0;
};

// Components of one type, packed densely. Removal moves the last element
// into the gap, which is deterministic given the same operations.
template <typename T>
class ComponentStore {
public:
    T* get(EntityId id) {
        const std::uint32_t d = dense_index(id);
        return d == kNone ? nullptr : &data_[d];
    }
    const T* get(EntityId id) const {
        const std::uint32_t d = dense_index(id);
        return d == kNone ? nullptr : &data_[d];
    }

    T& add(EntityId id, const T& value) {
        const std::uint32_t d = dense_index(id);
        if (d != kNone) {
            data_[d] = value;
            return data_[d];
        }
        if (id.index >= sparse_.size()) {
            sparse_.resize(id.index + 1, kNone);
        }
        sparse_[id.index] = static_cast<std::uint32_t>(entities_.size());
        entities_.push_back(id);
        data_.push_back(value);
        return data_.back();
    }

    bool remove(EntityId id) {
        const std::uint32_t d = dense_index(id);
        if (d == kNone) {
            return false;
        }
        const std::uint32_t last = static_cast<std::uint32_t>(entities_.size()) - 1;
        if (d != last) {
            entities_[d] = entities_[last];
            data_[d] = data_[last];
            sparse_[entities_[d].index] = d;
        }
        entities_.pop_back();
        data_.pop_back();
        sparse_[id.index] = kNone;
        return true;
    }

    [[nodiscard]] std::size_t size() const { return data_.size(); }
    [[nodiscard]] const std::vector<EntityId>& entities() const { return entities_; }
    [[nodiscard]] std::vector<T>& data() { return data_; }
    [[nodiscard]] const std::vector<T>& data() const { return data_; }

    void clear() {
        sparse_.clear();
        entities_.clear();
        data_.clear();
    }

    bool operator==(const ComponentStore&) const = default;

private:
    static constexpr std::uint32_t kNone = std::numeric_limits<std::uint32_t>::max();

    [[nodiscard]] std::uint32_t dense_index(EntityId id) const {
        if (id.index >= sparse_.size()) {
            return kNone;
        }
        const std::uint32_t d = sparse_[id.index];
        return (d != kNone && entities_[d] == id) ? d : kNone;
    }

    std::vector<std::uint32_t> sparse_;
    std::vector<EntityId> entities_;
    std::vector<T> data_;
};

}  // namespace sc::sim
