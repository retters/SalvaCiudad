#include "game/day_light.h"

#include <algorithm>
#include <cmath>

namespace sc {

namespace {

constexpr float kPi = 3.14159265f;
// Dawn and dusk take this much of the day (and of the night) each.
constexpr float kTwilight = 0.12f;
// The low sun is warm for this much of the day at each end.
constexpr float kWarm = 0.28f;
// The sun and the moon never go lower than this (as the height of a unit
// vector): the shadows would stretch across the whole map.
constexpr float kLowest = 0.16f;

// The night with no light near (the user chose a dark one).
constexpr math::Vec3 kMoonColor{0.16f, 0.21f, 0.34f};
constexpr math::Vec3 kNightSky{0.030f, 0.042f, 0.075f};
constexpr math::Vec3 kNightGround{0.010f, 0.011f, 0.018f};
constexpr math::Vec3 kNightZenith{0.003f, 0.006f, 0.020f};
constexpr math::Vec3 kNightHorizon{0.010f, 0.016f, 0.036f};
// How bright the water is with no moon, and what the moon adds.
constexpr float kNightWater = 0.05f;
constexpr float kMoonWater = 0.06f;
// Dawn and dusk.
constexpr math::Vec3 kWarmSun{1.0f, 0.55f, 0.28f};
constexpr math::Vec3 kWarmHorizon{0.95f, 0.52f, 0.30f};

float smooth(float edge0, float edge1, float x) {
    const float t = std::clamp((x - edge0) / (edge1 - edge0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

math::Vec3 mix(const math::Vec3& a, const math::Vec3& b, float t) {
    return {a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t};
}

math::Vec3 times(const math::Vec3& a, const math::Vec3& b) {
    return {a.x * b.x, a.y * b.y, a.z * b.z};
}

// From the east, over the south (or the north, for the moon), to the west.
math::Vec3 arc(float progress, float side) {
    const float a = kPi * std::clamp(progress, 0.0f, 1.0f);
    return math::normalize({std::cos(a), kLowest + (1.0f - kLowest) * std::sin(a), side});
}

}  // namespace

float day_progress(const sim::DayNightSettings& d, std::uint64_t tick, float tick_fraction) {
    if (!d.enabled()) {
        return 0.5f;
    }
    const sim::DayTime t = sim::day_time(d, tick);
    const float length = static_cast<float>((t.night ? d.night : d.day) * sim::kTicksPerMinute);
    const float in = length - static_cast<float>(t.ticks_left) + std::clamp(tick_fraction, 0.0f, 1.0f);
    return std::clamp(in / length, 0.0f, 1.0f);
}

float daylight(bool night, float progress) {
    const float edge = std::min(progress, 1.0f - progress);
    return night ? 0.0f : smooth(0.0f, kTwilight, edge);
}

render::Lighting day_lighting(const render::Lighting& season, bool night, float progress) {
    render::Lighting l = season;
    const float edge = std::min(progress, 1.0f - progress);
    // The sun, or the moon, rises out of the dark and sinks back into it.
    const float up = smooth(0.0f, kTwilight, edge);
    if (night) {
        l.sun_direction = arc(progress, -0.45f);
        l.sun_color = kMoonColor * up;
        l.sky_ambient = kNightSky;
        l.ground_ambient = kNightGround;
        l.zenith_color = kNightZenith;
        l.horizon_color = kNightHorizon;
        l.stars = 1.0f;
        l.disc = 5.0f;
        l.water = kNightWater + kMoonWater * up;
        return l;
    }
    const float warm = 1.0f - smooth(kTwilight * 0.5f, kWarm, edge);
    l.sun_direction = arc(progress, 0.45f);
    l.sun_color = times(season.sun_color, mix({1.0f, 1.0f, 1.0f}, kWarmSun, warm)) * up;
    l.sky_ambient = mix(kNightSky, season.sky_ambient, up);
    l.ground_ambient = mix(kNightGround, season.ground_ambient, up);
    l.zenith_color = mix(kNightZenith, season.zenith_color, up);
    l.horizon_color = mix(kNightHorizon, mix(season.horizon_color, kWarmHorizon, warm * 0.8f), up);
    l.stars = 1.0f - smooth(0.0f, kTwilight * 0.7f, edge);
    l.water = kNightWater + (1.0f - kNightWater) * up;
    return l;
}

render::Lighting rain_lighting(const render::Lighting& clear, float amount) {
    const float a = std::clamp(amount, 0.0f, 1.0f);
    if (a <= 0.0f) {
        return clear;
    }
    render::Lighting l = clear;
    // As bright as it was (it rains by night too), without its color.
    const auto gray = [](math::Vec3 c, float keep) {
        const float y = (0.30f * c.x + 0.55f * c.y + 0.15f * c.z) * keep;
        return math::Vec3{y * 0.95f, y, y * 1.06f};
    };
    l.zenith_color = mix(clear.zenith_color, gray(clear.zenith_color, 1.15f), a * 0.9f);
    l.horizon_color = mix(clear.horizon_color, gray(clear.horizon_color, 0.9f), a * 0.9f);
    l.sky_ambient = mix(clear.sky_ambient, gray(clear.sky_ambient, 0.95f), a * 0.8f);
    l.sun_color = clear.sun_color * (1.0f - 0.6f * a);
    l.disc = clear.disc * (1.0f - a);
    l.stars = clear.stars * (1.0f - a);
    l.water = clear.water * (1.0f - 0.25f * a);
    return l;
}

}  // namespace sc
