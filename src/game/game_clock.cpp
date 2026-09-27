#include "game/game_clock.h"

#include <algorithm>

namespace sc {

void GameClock::set_speed(int speed) {
    const int clamped = std::clamp(speed, 0, kMaxSpeed);
    if (clamped == speed_) {
        return;
    }
    // Keep the fraction of the current tick when the speed changes, so the
    // interpolation does not jump.
    if (clamped > 0) {
        accumulator_ns_ = accumulator_ns_ * running_speed_ / clamped;
        running_speed_ = clamped;
    }
    speed_ = clamped;
}

int GameClock::advance(std::int64_t real_elapsed_ns) {
    if (speed_ == 0) {
        return 0;
    }
    accumulator_ns_ += std::clamp<std::int64_t>(real_elapsed_ns, 0, kMaxFrameNs);
    const std::int64_t step = tick_real_ns();
    std::int64_t due = accumulator_ns_ / step;
    accumulator_ns_ -= due * step;
    if (due > kMaxTicksPerFrame) {
        dropped_ticks_ += static_cast<std::uint64_t>(due - kMaxTicksPerFrame);
        due = kMaxTicksPerFrame;
    }
    total_ticks_ += static_cast<std::uint64_t>(due);
    return static_cast<int>(due);
}

double GameClock::interpolation() const {
    // While paused the fraction stays frozen where it was.
    return static_cast<double>(accumulator_ns_) / static_cast<double>(tick_real_ns());
}

}  // namespace sc
