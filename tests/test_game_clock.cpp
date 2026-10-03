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
        clock.set_speed(12);
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
        clock.set_speed(4);
        CHECK(clock.advance(50 * kMs) == 1);
    }

    TEST_CASE("speed changes keep the fraction of the current tick") {
        GameClock clock;
        CHECK(clock.advance(50 * kMs) == 0);
        CHECK(clock.interpolation() == doctest::Approx(0.5));
        clock.set_speed(8);
        CHECK(clock.interpolation() == doctest::Approx(0.5));
        CHECK(clock.advance(25 * kMs) == 1);
    }

    TEST_CASE("long stalls are capped instead of racing to catch up") {
        GameClock clock;
        clock.set_speed(12);
        // A 10 s stall counts as 250 ms: 7 ticks of 33.3 ms at x3.
        const int ticks = clock.advance(10'000 * kMs);
        CHECK(ticks == 7);
        CHECK(ticks <= GameClock::kMaxTicksPerFrame);
        CHECK(clock.dropped_ticks() == 0);
    }

    TEST_CASE("speeds are clamped and negative time is ignored") {
        GameClock clock;
        clock.set_speed(99);
        CHECK(clock.speed() == GameClock::kMaxSpeed);
        clock.set_speed(-1);
        CHECK(clock.speed() == 0);
        clock.set_speed(4);
        CHECK(clock.advance(-5 * kMs) == 0);
    }

    TEST_CASE("speeds are quarters of the normal one, from x0.25 to x9") {
        // Each step runs its share of ticks in ten seconds of 60 Hz frames.
        for (const int quarters : sc::speed::kSteps) {
            GameClock clock;
            clock.set_speed(quarters);
            CHECK(clock.speed() == quarters);
            int ticks = 0;
            for (int i = 0; i < 600; ++i) {
                ticks += clock.advance(16'666'667);
            }
            CHECK(ticks == 25 * quarters);  // 100 ticks at x1.
            CHECK(clock.dropped_ticks() == 0);
        }
        // What is not a step becomes the one below it.
        GameClock clock;
        clock.set_speed(3);
        CHECK(clock.speed() == 2);
        clock.set_speed(15);
        CHECK(clock.speed() == 12);
        // The table: up and down, and the cap of a game with others.
        CHECK(sc::speed::faster(4) == 8);
        CHECK(sc::speed::faster(20) == 24);
        CHECK(sc::speed::faster(20, sc::speed::kMaxNetwork) == 20);
        CHECK(sc::speed::faster(36) == 36);
        CHECK(sc::speed::slower(4) == 2);
        CHECK(sc::speed::slower(1) == 1);
        CHECK(sc::speed::snap(36, sc::speed::kMaxNetwork) == 20);
        CHECK(sc::speed::multiplier(1) == doctest::Approx(0.25f));
        CHECK(sc::speed::multiplier(36) == doctest::Approx(9.0f));
    }

    TEST_CASE("a slow speed keeps the interpolation smooth") {
        GameClock clock;
        clock.set_speed(1);  // x0.25: a tick every 400 ms.
        CHECK(clock.advance(100 * kMs) == 0);
        CHECK(clock.interpolation() == doctest::Approx(0.25));
        CHECK(clock.advance(200 * kMs) == 0);  // A frame counts 250 ms at most.
        CHECK(clock.advance(100 * kMs) == 1);
    }
}
