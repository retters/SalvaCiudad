// Where each model's instances live in the instance buffer (phase 130).
#include <doctest.h>

#include <algorithm>
#include <cstdint>
#include <vector>

#include "render/instance_layout.h"

using namespace sc::render;

namespace {

// No two slots share a place, and all of them fit in the buffer.
bool slots_apart(const InstanceLayout& layout) {
    std::vector<InstanceLayout::Slot> slots;
    for (std::size_t m = 0; m < layout.models(); ++m) {
        if (layout.slot(m).capacity > 0) {
            slots.push_back(layout.slot(m));
        }
    }
    std::sort(slots.begin(), slots.end(), [](const auto& a, const auto& b) { return a.base < b.base; });
    for (std::size_t i = 0; i < slots.size(); ++i) {
        if (slots[i].base + slots[i].capacity > layout.end() || layout.end() > layout.capacity()) {
            return false;
        }
        if (i > 0 && slots[i - 1].base + slots[i - 1].capacity > slots[i].base) {
            return false;
        }
    }
    return true;
}

}  // namespace

TEST_SUITE("scene") {
    TEST_CASE("a small list that grows moves alone and seldom lays everything out again") {
        InstanceLayout layout;
        layout.resize(4);
        // A colossal map: two big models and two small lists (rain, smoke).
        layout.reserve(0, 1'000'000);
        layout.reserve(1, 800'000);
        CHECK(slots_apart(layout));
        const InstanceLayout::Slot big0 = layout.slot(0);
        const InstanceLayout::Slot big1 = layout.slot(1);
        int relaid = 0;
        int moved = 0;
        for (std::uint32_t n = 1; n <= 20'000; ++n) {
            for (const std::size_t m : {std::size_t{2}, std::size_t{3}}) {
                switch (layout.reserve(m, m == 2 ? n : n / 3)) {
                    case InstanceLayout::Change::Relaid: ++relaid; break;
                    case InstanceLayout::Change::Moved: ++moved; break;
                    case InstanceLayout::Change::None: break;
                }
                REQUIRE(layout.slot(m).capacity >= (m == 2 ? n : n / 3));
            }
        }
        CHECK(slots_apart(layout));
        // Each move gives a quarter more room, so a list going from 1 to
        // 20 000 moves a few dozen times, and the room left at the end of
        // the buffer takes all of those moves.
        CHECK(moved < 80);
        CHECK(relaid == 0);
        CHECK(layout.slot(0).base == big0.base);
        CHECK(layout.slot(1).base == big1.base);
        CHECK(layout.abandoned() > 0);
    }

    TEST_CASE("when the end of the buffer is full everything is packed again") {
        InstanceLayout layout;
        layout.reserve(0, 1000);
        layout.reserve(1, 10);
        const std::uint32_t capacity = layout.capacity();
        int relaid = 0;
        std::uint32_t n = 10;
        while (relaid == 0) {
            n = n * 2;
            REQUIRE(n < 100'000'000u);
            if (layout.reserve(1, n) == InstanceLayout::Change::Relaid) {
                ++relaid;
            }
        }
        CHECK(slots_apart(layout));
        CHECK(layout.abandoned() == 0);
        CHECK(layout.capacity() > capacity);
        // Packed: the first model's slot fits its instances with room, and
        // the second follows right after it.
        CHECK(layout.slot(0).base == 0);
        CHECK(layout.slot(0).capacity >= 1000);
        CHECK(layout.slot(1).base == layout.slot(0).capacity);
        CHECK(layout.slot(1).capacity >= n);
        CHECK(layout.end() == layout.slot(1).base + layout.slot(1).capacity);
    }

    TEST_CASE("models with nothing take no room and slots never overlap") {
        InstanceLayout layout;
        layout.resize(6);
        CHECK(layout.reserve(5, 0) == InstanceLayout::Change::None);
        CHECK(layout.end() == 0);
        // A made-up sequence of growing and shrinking lists.
        std::uint32_t seed = 12345;
        for (int step = 0; step < 5000; ++step) {
            seed = seed * 1664525u + 1013904223u;
            const std::size_t m = (seed >> 8) % 6;
            const std::uint32_t count = (seed >> 12) % (m == 0 ? 200'000u : 3000u);
            layout.reserve(m, count);
            REQUIRE(layout.slot(m).capacity >= count);
            REQUIRE(slots_apart(layout));
        }
        // Emptied, a model keeps its slot: nothing moves for it.
        const InstanceLayout::Slot before = layout.slot(3);
        CHECK(layout.reserve(3, 0) == InstanceLayout::Change::None);
        CHECK(layout.slot(3).base == before.base);
        layout.clear();
        CHECK(layout.models() == 0);
        CHECK(layout.end() == 0);
    }
}
