#include <doctest.h>

#include "game/game_clock.h"

using namespace sc;

namespace {
constexpr std::int64_t kMs = 1'000'000;
}

TEST_SUITE("game_clock") {
    TEST_CASE("one tick per 100 ms at x1") {
        GameClock clock;
        CHECK(clock.advance(99 * kMs) == 0);
        CHECK(clock.advance(1 * kMs) == 1);
        CHECK(clock.advance(250 * kMs) == 2);
        CHECK(clock.total_ticks() == 3);
        CHECK(clock.interpolation() == doctest::Approx(0.5));
    }

    TEST_CASE("x3 runs three times as many ticks") {
        GameClock clock;
        clock.set_speed(3);
        int ticks = 0;
        for (int i = 0; i < 60; ++i) {
            ticks += clock.advance(16'666'667);  // One 60 Hz frame, rounded up.
        }
        CHECK(ticks == 30);
    }

    TEST_CASE("pause stops ticks and freezes the interpolation") {
        GameClock clock;
        CHECK(clock.advance(150 * kMs) == 1);
        const double before = clock.interpolation();
        clock.set_speed(0);
        CHECK(clock.advance(1000 * kMs) == 0);
        CHECK(clock.interpolation() == doctest::Approx(before));
        clock.set_speed(1);
        CHECK(clock.advance(50 * kMs) == 1);
    }

    TEST_CASE("speed changes keep the fraction of the current tick") {
        GameClock clock;
        CHECK(clock.advance(50 * kMs) == 0);
        CHECK(clock.interpolation() == doctest::Approx(0.5));
        clock.set_speed(2);
        CHECK(clock.interpolation() == doctest::Approx(0.5));
        CHECK(clock.advance(25 * kMs) == 1);
    }

    TEST_CASE("long stalls are capped instead of racing to catch up") {
        GameClock clock;
        clock.set_speed(3);
        // A 10 s stall counts as 250 ms: 7 ticks of 33.3 ms at x3.
        const int ticks = clock.advance(10'000 * kMs);
        CHECK(ticks == 7);
        CHECK(ticks <= GameClock::kMaxTicksPerFrame);
        CHECK(clock.dropped_ticks() == 0);
    }

    TEST_CASE("speeds are clamped and negative time is ignored") {
        GameClock clock;
        clock.set_speed(9);
        CHECK(clock.speed() == GameClock::kMaxSpeed);
        clock.set_speed(-1);
        CHECK(clock.speed() == 0);
        clock.set_speed(1);
        CHECK(clock.advance(-5 * kMs) == 0);
    }
}
