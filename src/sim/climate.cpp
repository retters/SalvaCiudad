#include "sim/climate.h"

#include <array>

namespace sc::sim {

namespace {

// Days of the month and months of the year never change; the year's
// length changes how long a day is.
constexpr std::uint32_t kMonths = 12;
constexpr std::uint32_t kDaysPerMonth = 10;

std::int32_t base_temperature(Season s, Harshness winter) {
    switch (s) {
        case Season::Spring: return 12;
        case Season::Summer: return 24;
        case Season::Autumn: return winter == Harshness::Harsh ? 7 : 11;
        case Season::Winter:
            return winter == Harshness::Mild ? 3 : (winter == Harshness::Harsh ? -14 : -4);
        case Season::Count: break;
    }
    return 12;
}

std::uint64_t mix(std::uint64_t x) {
    x ^= x >> 33;
    x *= 0xFF51AFD7ED558CCDull;
    x ^= x >> 33;
    x *= 0xC4CEB9FE1A85EC53ull;
    x ^= x >> 33;
    return x;
}

}  // namespace

void GameRules::write(BinaryWriter& w) const {
    w.u8(climate.seasons);
    w.u8(static_cast<std::uint8_t>(climate.year));
    w.u8(static_cast<std::uint8_t>(climate.winter));
    w.u8(static_cast<std::uint8_t>(start));
    w.i32(max_population);
}

bool GameRules::read(BinaryReader& r, GameRules& out) {
    GameRules g;
    std::uint8_t year = 0, winter = 0, start = 0;
    if (!r.u8(g.climate.seasons) || !r.u8(year) || !r.u8(winter) || !r.u8(start) || !r.i32(g.max_population)) {
        return false;
    }
    if (g.climate.seasons == 0 || g.climate.seasons > 0b1111 || year >= static_cast<std::uint8_t>(YearLength::Count) ||
        winter >= static_cast<std::uint8_t>(Harshness::Count) || start >= static_cast<std::uint8_t>(StartGoods::Count) ||
        g.max_population < kMinPopulationLimit || g.max_population > kMaxPopulationLimit) {
        r.fail();
        return false;
    }
    g.climate.year = static_cast<YearLength>(year);
    g.climate.winter = static_cast<Harshness>(winter);
    g.start = static_cast<StartGoods>(start);
    out = g;
    return true;
}

std::uint32_t year_ticks(YearLength length) {
    switch (length) {
        case YearLength::Short: return 6000;
        case YearLength::Long: return 24000;
        default: return 12000;
    }
}

Calendar calendar(const ClimateSettings& c, std::uint64_t tick) {
    const std::uint64_t year = year_ticks(c.year);
    const std::uint64_t in_year = tick % year;
    const std::uint64_t month_ticks = year / kMonths;
    const std::uint64_t day_ticks = month_ticks / kDaysPerMonth;
    Calendar cal;
    cal.year = static_cast<std::uint32_t>(tick / year) + 1;
    cal.month = static_cast<std::uint32_t>(in_year / month_ticks) + 1;
    cal.day = static_cast<std::uint32_t>(in_year % month_ticks / day_ticks) + 1;
    // The enabled seasons in order, each an equal part of the year.
    std::array<Season, 4> enabled{};
    std::uint32_t n = 0;
    for (std::uint8_t s = 0; s < 4; ++s) {
        if (((c.seasons >> s) & 1u) != 0) {
            enabled[n++] = static_cast<Season>(s);
        }
    }
    if (n == 0) {
        enabled[n++] = Season::Summer;
    }
    const std::uint64_t part = in_year * n;
    cal.season = enabled[static_cast<std::size_t>(part / year)];
    cal.season_progress = static_cast<std::uint32_t>(part % year * 1000 / year);
    return cal;
}

std::int32_t temperature(const ClimateSettings& c, std::uint64_t seed, std::uint64_t tick) {
    const Calendar cal = calendar(c, tick);
    std::int32_t t = base_temperature(cal.season, c.winter);
    // The first quarter of a season eases in from the one before.
    std::uint32_t n = 0;
    std::uint32_t index = 0;
    std::array<Season, 4> enabled{};
    for (std::uint8_t s = 0; s < 4; ++s) {
        if (((c.seasons >> s) & 1u) != 0) {
            if (static_cast<Season>(s) == cal.season) {
                index = n;
            }
            enabled[n++] = static_cast<Season>(s);
        }
    }
    if (n > 1 && cal.season_progress < 250) {
        const Season before = enabled[(index + n - 1) % n];
        const std::int32_t from = base_temperature(before, c.winter);
        t = from + (t - from) * static_cast<std::int32_t>(cal.season_progress) / 250;
    }
    // A little variation from day to day, the same everywhere.
    const std::uint64_t day = tick / (year_ticks(c.year) / (kMonths * kDaysPerMonth));
    t += static_cast<std::int32_t>(mix(seed ^ (day * 0x9E3779B97F4A7C15ull)) % 7) - 3;
    return t;
}

}  // namespace sc::sim
