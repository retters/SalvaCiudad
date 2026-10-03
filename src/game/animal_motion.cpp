#include "game/animal_motion.h"

#include <cmath>

namespace sc::animal_motion {

void advance(const Clips& c, State& s, float speed, float game_dt, float rest_dt, std::uint32_t seed) {
    if (speed > 0.0f) {
        const bool run = speed > c.walk_speed * kRunAbove;
        const std::uint32_t clip = run ? c.run : c.walk;
        const float length = run ? c.run_length : c.walk_length;
        if (s.clip == c.walk || s.clip == c.run) {
            if (s.clip != clip) {  // The same point of the stride in the other gait.
                s.time = s.time / (s.clip == c.walk ? c.walk_length : c.run_length) * length;
            }
        } else {
            s.time = 0.0f;
        }
        s.clip = clip;
        s.time = std::fmod(s.time + game_dt * speed / (run ? c.run_speed : c.walk_speed), length);
        return;
    }
    // Eat comes twice as often as idle.
    const auto pick = [&] {
        const std::uint32_t h = (seed * 2654435761u) ^ (s.rests * 40503u);
        return (h >> 7) % 3u == 0 ? c.idle : c.eat;
    };
    if (s.clip != c.idle && s.clip != c.eat) {
        s.clip = pick();
        s.time = 0.0f;
    }
    s.time += rest_dt;
    const float length = s.clip == c.idle ? c.idle_length : c.eat_length;
    if (s.time >= length) {
        s.time = std::fmod(s.time, length);
        ++s.rests;
        s.clip = pick();
    }
}

}  // namespace sc::animal_motion
