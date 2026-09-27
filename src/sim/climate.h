// Seasons and weather (phase 10, sections 6.3 and 7.9), and the other
// rules chosen when a game is set up. All integer and a pure function of
// the rules, the game's seed and the tick, except the snow, which the game
// keeps as state.
#pragma once

#include <cstdint>

#include "sim/serialize.h"

namespace sc::sim {

enum class Season : std::uint8_t { Spring, Summer, Autumn, Winter, Count };
enum class YearLength : std::uint8_t { Short, Normal, Long, Count };
enum class Harshness : std::uint8_t { Mild, Normal, Harsh, Count };
enum class StartGoods : std::uint8_t { Scarce, Normal, Plenty, Count };
// How much of a threat the surroundings are (section 6.3).
enum class Threat : std::uint8_t { None, Low, Medium, High, Brutal, Count };
// Chances scale with the threat: 0, 50, 100, 200 or 400 %.
[[nodiscard]] std::int32_t threat_percent(Threat t);

struct ClimateSettings {
    std::uint8_t seasons = 0b1111;  // Bit per Season; at least one.
    YearLength year = YearLength::Normal;
    Harshness winter = Harshness::Normal;
    bool operator==(const ClimateSettings&) const = default;
};

// Everything chosen for a game besides the map.
struct GameRules {
    ClimateSettings climate;
    StartGoods start = StartGoods::Normal;
    std::int32_t max_population = 1000;  // Per player, 50..1000.
    Threat diseases = Threat::Medium;
    Threat fires = Threat::Medium;

    void write(BinaryWriter& w) const;
    [[nodiscard]] static bool read(BinaryReader& r, GameRules& out);
    bool operator==(const GameRules&) const = default;
};

inline constexpr std::int32_t kMinPopulationLimit = 50;
inline constexpr std::int32_t kMaxPopulationLimit = 1000;

// Ticks in a year: about 10, 20 or 40 minutes at x1.
[[nodiscard]] std::uint32_t year_ticks(YearLength length);

struct Calendar {
    std::uint32_t year = 1;   // From 1.
    std::uint32_t month = 1;  // 1..12
    std::uint32_t day = 1;    // 1..10 (days of the month)
    Season season = Season::Spring;
    // Fraction of the way through the season, 0..999.
    std::uint32_t season_progress = 0;
};

// Twelve months of ten days each; the enabled seasons share the year in
// order (with one season, it lasts all year).
[[nodiscard]] Calendar calendar(const ClimateSettings& c, std::uint64_t tick);

// The day's temperature in whole degrees Celsius: each season's base,
// easing in from the previous one, plus a small daily variation.
[[nodiscard]] std::int32_t temperature(const ClimateSettings& c, std::uint64_t seed, std::uint64_t tick);

}  // namespace sc::sim
