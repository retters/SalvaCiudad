// The game's speeds (phase 58). A speed is a whole number of quarters of
// the normal one: 4 is x1, 1 is x0.25, 20 is x5. 0 is the pause. Only the
// steps of the table exist; a network game stops at kMaxNetwork.
#pragma once

#include <algorithm>
#include <iterator>

namespace sc::speed {

inline constexpr int kPause = 0;
inline constexpr int kNormal = 4;  // x1.
inline constexpr int kSteps[] = {1, 2, 4, 8, 12, 16, 20, 24, 28, 32, 36};
inline constexpr int kMin = 1;          // x0.25.
inline constexpr int kMax = 36;         // x9, alone.
inline constexpr int kMaxNetwork = 20;  // x5, with others.

// Whether `quarters` is the pause or one of the steps.
[[nodiscard]] constexpr bool valid(int quarters) {
    return quarters == kPause || std::find(std::begin(kSteps), std::end(kSteps), quarters) != std::end(kSteps);
}

// The pause, or the fastest step that is not over `quarters` nor `max`.
[[nodiscard]] constexpr int snap(int quarters, int max = kMax) {
    if (quarters <= 0) {
        return kPause;
    }
    int best = kMin;
    for (const int s : kSteps) {
        if (s <= quarters && s <= max) {
            best = s;
        }
    }
    return best;
}

// The next step up (at most `max`) or down; the ends stay where they are.
[[nodiscard]] constexpr int faster(int quarters, int max = kMax) {
    for (const int s : kSteps) {
        if (s > quarters && s <= max) {
            return s;
        }
    }
    return snap(quarters, max);
}
[[nodiscard]] constexpr int slower(int quarters) {
    int best = kMin;
    for (const int s : kSteps) {
        if (s < quarters) {
            best = s;
        }
    }
    return best;
}

// How many times the normal speed it is: 0.25 .. 9, or 0 for the pause.
[[nodiscard]] constexpr float multiplier(int quarters) {
    return static_cast<float>(quarters) / static_cast<float>(kNormal);
}

}  // namespace sc::speed
