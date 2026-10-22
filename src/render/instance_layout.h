// Where each model's instances live in the scene's instance buffer (phase
// 130). Every model has a slot: a run of places it may fill. A model that
// outgrows its slot moves to the end of the buffer with room to spare, and
// the others stay where they are; only when the buffer has no room left at
// the end is everything laid out again, packed, with room at the end for
// the moves to come.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace sc::render {

class InstanceLayout {
public:
    struct Slot {
        std::uint32_t base = 0;      // First place.
        std::uint32_t capacity = 0;  // Places it may fill.
    };
    enum class Change : std::uint8_t {
        None,   // It fits where it is.
        Moved,  // Only this model moved (to the end).
        Relaid  // Every model may have moved.
    };

    // Models that are not there yet get an empty slot (and need nothing).
    void resize(std::size_t models);
    [[nodiscard]] std::size_t models() const { return slots_.size(); }

    // Model `model` now holds `count` instances.
    Change reserve(std::size_t model, std::uint32_t count);

    [[nodiscard]] const Slot& slot(std::size_t model) const { return slots_[model]; }
    // Places up to the end of the last slot: what the buffer must hold.
    [[nodiscard]] std::uint32_t end() const { return end_; }
    // Places the buffer has (end() plus room for moves).
    [[nodiscard]] std::uint32_t capacity() const { return capacity_; }
    // Places of slots that were left behind by a move.
    [[nodiscard]] std::uint32_t abandoned() const { return abandoned_; }
    void clear();

    // Room for `count` instances in a slot laid out or moved now.
    [[nodiscard]] static std::uint32_t room_for(std::uint32_t count);
    // How many places the buffer gets for `used` packed ones.
    [[nodiscard]] static std::uint32_t buffer_for(std::uint32_t used);

private:
    void lay_out();

    std::vector<Slot> slots_;
    std::vector<std::uint32_t> counts_;
    std::uint32_t end_ = 0;
    std::uint32_t capacity_ = 0;
    std::uint32_t abandoned_ = 0;
};

}  // namespace sc::render
