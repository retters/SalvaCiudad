// Which clip an animated animal plays and how far into it (phase 47).
// Presentation only: it reads how far the animal moved and never feeds
// back into the simulation.
#pragma once

#include <cstdint>

namespace sc::animal_motion {

// The clips of one species and what they were made for.
struct Clips {
    std::uint32_t idle = 0, walk = 0, run = 0, eat = 0;
    float walk_speed = 1.0f;  // m/s at which the walk's feet do not slide.
    float run_speed = 3.0f;
    float idle_length = 1.0f, walk_length = 1.0f, run_length = 1.0f, eat_length = 1.0f;  // Seconds.
};

// What one animal is playing.
struct State {
    std::uint32_t clip = ~0u;
    float time = 0.0f;         // Seconds into `clip`, within its length.
    std::uint32_t rests = 0;   // Idle and eat loops played, to pick the next one.
};

// Above this many times the walk's speed, the animal runs.
inline constexpr float kRunAbove = 1.5f;

// Advances `s` for an animal moving at `speed` m/s of game time (0:
// standing). A moving animal walks or runs by its speed, with the clip
// played at the rate that keeps its feet planted; a change of gait keeps
// the point of the stride. A standing one plays idle or eat, picking again
// at the end of each loop (both start and end in the same pose) from
// `seed` and the loops played. `game_dt` is the game time passed; `rest_dt`
// the time for idle and eat.
void advance(const Clips& c, State& s, float speed, float game_dt, float rest_dt, std::uint32_t seed);

}  // namespace sc::animal_motion
