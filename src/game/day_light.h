// The light of the time of day (phase 68): from a season's daylight and how
// far the day or the night has gone, the sun or the moon in its place, the
// colors of dawn and dusk and the dark of the night. Presentation only.
#pragma once

#include "render/scene_renderer.h"
#include "sim/climate.h"

namespace sc {

// How far the day or the night has gone, 0 to 1, with the fraction of the
// tick being shown.
[[nodiscard]] float day_progress(const sim::DayNightSettings& d, std::uint64_t tick, float tick_fraction = 0.0f);

// How much of the daylight there is: 1 through the day, 0 through the
// night, easing at dawn and dusk.
[[nodiscard]] float daylight(bool night, float progress);

// `season` as it is at that time. With no cycle, pass night = false and
// progress = 0.5 (noon) or do not call it.
[[nodiscard]] render::Lighting day_lighting(const render::Lighting& season, bool night, float progress);

// Phase 97: the same light under the rain (or the snow), `amount` from 0
// (clear) to 1: a gray sky, a weak sun without its disc, no stars.
[[nodiscard]] render::Lighting rain_lighting(const render::Lighting& clear, float amount);

}  // namespace sc
