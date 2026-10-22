#include "render/instance_layout.h"

#include <algorithm>
#include <limits>

namespace sc::render {

namespace {

// Never more places than a 32-bit byte size of 64-byte instances holds.
constexpr std::uint64_t kMaxPlaces = std::numeric_limits<std::uint32_t>::max() / 64;

std::uint32_t clamp_places(std::uint64_t places) {
    return static_cast<std::uint32_t>(std::min(places, kMaxPlaces));
}

}  // namespace

std::uint32_t InstanceLayout::room_for(std::uint32_t count) {
    // A quarter more and a little extra: lists that start empty (smoke,
    // rain, animals) get room before they need it.
    return clamp_places(std::uint64_t{count} + count / 4 + 64);
}

std::uint32_t InstanceLayout::buffer_for(std::uint32_t used) {
    // Room at the end for many moves of the small lists before the next
    // packing; a quarter more for the big ones.
    return clamp_places(std::uint64_t{used} + used / 4 + 65536);
}

void InstanceLayout::resize(std::size_t models) {
    if (models > slots_.size()) {
        // New models start with nothing: their first reserve gives them room.
        slots_.resize(models, Slot{end_, 0});
        counts_.resize(models, 0);
    }
}

InstanceLayout::Change InstanceLayout::reserve(std::size_t model, std::uint32_t count) {
    resize(model + 1);
    counts_[model] = count;
    Slot& s = slots_[model];
    if (count <= s.capacity) {
        return Change::None;
    }
    const std::uint32_t room = room_for(count);
    if (std::uint64_t{end_} + room <= capacity_) {
        abandoned_ += s.capacity;
        s.base = end_;
        s.capacity = room;
        end_ += room;
        return Change::Moved;
    }
    lay_out();
    return Change::Relaid;
}

void InstanceLayout::lay_out() {
    std::uint64_t base = 0;
    for (std::size_t m = 0; m < slots_.size(); ++m) {
        // A model with nothing and no room keeps none: models never filled
        // (the far versions, the looks) cost no places.
        const std::uint32_t room = counts_[m] == 0 && slots_[m].capacity == 0 ? 0 : room_for(counts_[m]);
        slots_[m] = Slot{clamp_places(base), room};
        base += room;
    }
    end_ = clamp_places(base);
    capacity_ = buffer_for(end_);
    abandoned_ = 0;
}

void InstanceLayout::clear() {
    *this = InstanceLayout{};
}

}  // namespace sc::render
