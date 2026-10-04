// Seasons and weather (phase 10, sections 6.3 and 7.9), and the other
// rules chosen when a game is set up. All integer and a pure function of
// the rules, the game's seed and the tick, except the snow, which the game
// keeps as state.
#pragma once

#include <array>
#include <cstdint>

#include "sim/serialize.h"

namespace sc::sim {

enum class Season : std::uint8_t { Spring, Summer, Autumn, Winter, Count };
// Phase 56: the length of the year is a percent of the usual one (20
// minutes at x1), from kMinYearPercent to 200. These name the three
// lengths of before.
struct YearLength {
    static constexpr std::uint8_t Short = 50, Normal = 100, Long = 200;
};
inline constexpr std::uint8_t kMinYearPercent = 25;
inline constexpr std::uint8_t kMaxYearPercent = 200;
enum class Harshness : std::uint8_t { Mild, Normal, Harsh, Count };
enum class StartGoods : std::uint8_t { Scarce, Normal, Plenty, Count };
// How much of a threat the surroundings are (section 6.3).
enum class Threat : std::uint8_t { None, Low, Medium, High, Brutal, Count };
inline constexpr std::uint8_t kMixedRace = 0xFF;

// How a versus game is won (section 6.3).
enum class Victory : std::uint8_t { None, Elimination, Score, Objective, Count };
// Fog of war (phases 32 and 33): none; what was explored stays in view; or
// what was explored stays dim and only what is in sight shows what moves.
// Revealed (phase 60) is the dynamic one with the whole map explored from
// the start.
enum class FogMode : std::uint8_t { None, Static, Dynamic, Revealed, Count };
// Whether the mode keeps what is in sight now and ghosts of what was seen.
[[nodiscard]] constexpr bool fog_is_dynamic(FogMode m) {
    return m == FogMode::Dynamic || m == FogMode::Revealed;
}
// Chances scale with the threat: 0, 50, 100, 200 or 400 %.
[[nodiscard]] std::int32_t threat_percent(Threat t);

// Phase 59: a season may have its own length, in minutes at x1.
inline constexpr std::uint8_t kMaxSeasonMinutes = 30;
inline constexpr std::uint32_t kTicksPerMinute = 600;

struct ClimateSettings {
    std::uint8_t seasons = 0b1111;  // Bit per Season; at least one.
    // Percent of the usual year, which the seasons share evenly; only when
    // no season has minutes of its own.
    std::uint8_t year = YearLength::Normal;
    Harshness winter = Harshness::Normal;
    // Minutes of each season at x1 (1..kMaxSeasonMinutes for the enabled
    // ones, 0 for the others), and the year is their sum; or all 0.
    std::array<std::uint8_t, 4> minutes{};

    // Whether the seasons have minutes of their own.
    [[nodiscard]] bool own_lengths() const { return minutes != std::array<std::uint8_t, 4>{}; }
    bool operator==(const ClimateSettings&) const = default;
};

// Phase 68: day and night, each with its minutes at x1. The cycle does not
// follow the calendar: it starts at dawn on the first tick and repeats.
// Both 0: no cycle, always day.
inline constexpr std::uint8_t kMaxDayMinutes = 30;
struct DayNightSettings {
    std::uint8_t day = 0;    // Minutes of day, 1..kMaxDayMinutes; or 0.
    std::uint8_t night = 0;  // Minutes of night, the same.

    [[nodiscard]] bool enabled() const { return day != 0 && night != 0; }
    bool operator==(const DayNightSettings&) const = default;
};

// Everything chosen for a game besides the map.
struct GameRules {
    ClimateSettings climate;
    StartGoods start = StartGoods::Normal;
    std::int32_t max_population = 1000;  // Per player, 50..1000.
    Threat diseases = Threat::Medium;
    Threat fires = Threat::Medium;
    Threat raiders = Threat::Medium;   // Phase 15.
    Threat wildlife = Threat::Medium;  // Wolves and bears.
    // Phase 16: cooperative (false) or versus; whether armies may attack
    // other players; how a versus game is won.
    bool versus = false;
    bool pvp = true;
    Victory victory = Victory::Elimination;
    std::int32_t score_years = 5;  // Score victory: the best score after this many years.
    // Phase 19: each player's people (a race index; kMixedRace: a mix) and
    // how many newcomers are of another race, percent.
    std::array<std::uint8_t, 12> races{};
    std::uint8_t other_races = 20;
    // Phase 56: the races that may come as newcomers of another race: bit i
    // is race i of the content. 0: all of them.
    std::uint16_t immigrants = 0;
    // Phase 32: fog of war (the new game form starts with static fog,
    // decision D-3202) and whether allies share what they see.
    FogMode fog = FogMode::None;
    bool shared_vision = true;
    // Phase 68: day and night.
    DayNightSettings day_night;

    void write(BinaryWriter& w) const;
    [[nodiscard]] static bool read(BinaryReader& r, GameRules& out);
    bool operator==(const GameRules&) const = default;
};

inline constexpr std::int32_t kMinPopulationLimit = 50;
inline constexpr std::int32_t kMaxPopulationLimit = 1000;
// Above this many villagers in all, the lobby warns that the game may run
// slowly (measured in phase 20: docs/RENDIMIENTO.md).
inline constexpr std::int32_t kPopulationWarning = 6000;

// Ticks in a year of that percent: about 10, 20 or 40 minutes at x1.
[[nodiscard]] std::uint32_t year_ticks(std::uint8_t percent);
// Ticks in the year of these settings: the percent's, or the sum of the
// seasons' minutes. Always a whole number of ticks per day (120 days).
[[nodiscard]] std::uint32_t year_ticks(const ClimateSettings& c);

// The enabled seasons in order with their lengths in ticks. Returns how
// many there are (at least one).
struct SeasonSpan {
    Season season = Season::Summer;
    std::uint32_t ticks = 0;
};
[[nodiscard]] std::uint32_t season_spans(const ClimateSettings& c, std::array<SeasonSpan, 4>& out);

struct Calendar {
    std::uint32_t year = 1;   // From 1.
    std::uint32_t month = 1;  // 1..12
    std::uint32_t day = 1;    // 1..10 (days of the month)
    Season season = Season::Spring;
    // Fraction of the way through the season, 0..999.
    std::uint32_t season_progress = 0;
};

// Twelve months of ten days each; the enabled seasons share the year in
// order, evenly or each with its minutes (with one season, it lasts all
// year).
[[nodiscard]] Calendar calendar(const ClimateSettings& c, std::uint64_t tick);

// The day's temperature in whole degrees Celsius: each season's base,
// easing in from the previous one, plus a small daily variation.
[[nodiscard]] std::int32_t temperature(const ClimateSettings& c, std::uint64_t seed, std::uint64_t tick);

// The time of day at a tick (phase 68).
struct DayTime {
    bool night = false;
    std::uint32_t progress = 0;    // Of the day or of the night, 0..999.
    std::uint32_t ticks_left = 0;  // Until the other one starts; 0 with no cycle.
};
[[nodiscard]] DayTime day_time(const DayNightSettings& d, std::uint64_t tick);

}  // namespace sc::sim
