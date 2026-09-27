// Fixed-step clock that turns real elapsed time into simulation ticks.
// The simulation always advances in whole ticks of 100 ms of game time
// (decision D-003); the game speed only changes how much real time a tick
// takes.
#pragma once

#include <cstdint>

namespace sc {

class GameClock {
public:
    static constexpr std::int64_t kTickGameNs = 100'000'000;  // 100 ms of game time.
    static constexpr int kMaxSpeed = 3;
    // Longest real frame accounted for; a longer stall (debugger, window drag)
    // is dropped instead of making the game race to catch up.
    static constexpr std::int64_t kMaxFrameNs = 250'000'000;
    static constexpr int kMaxTicksPerFrame = 8;

    // 0 pauses; 1..kMaxSpeed multiplies the game speed. Out-of-range values
    // are clamped.
    void set_speed(int speed);
    [[nodiscard]] int speed() const { return speed_; }

    // Adds real elapsed time and returns how many ticks to simulate now.
    int advance(std::int64_t real_elapsed_ns);

    // Fraction of the next tick already elapsed, for interpolating the
    // presentation between the last two ticks. In [0, 1).
    [[nodiscard]] double interpolation() const;

    [[nodiscard]] std::uint64_t total_ticks() const { return total_ticks_; }
    // Ticks that were due but skipped because the frame budget ran out.
    [[nodiscard]] std::uint64_t dropped_ticks() const { return dropped_ticks_; }

private:
    [[nodiscard]] std::int64_t tick_real_ns() const { return kTickGameNs / running_speed_; }

    int speed_ = 1;
    int running_speed_ = 1;  // Last non-zero speed; the accumulator is measured at it.
    std::int64_t accumulator_ns_ = 0;
    std::uint64_t total_ticks_ = 0;
    std::uint64_t dropped_ticks_ = 0;
};

}  // namespace sc
