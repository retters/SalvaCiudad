#include "sim/climate.h"

#include <algorithm>

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

std::int32_t threat_percent(Threat t) {
    static constexpr std::int32_t kPercent[] = {0, 50, 100, 200, 400};
    return kPercent[static_cast<std::size_t>(t) % std::size(kPercent)];
}

void GameRules::write(BinaryWriter& w) const {
    w.u8(climate.seasons);
    w.u8(climate.year);
    w.u8(static_cast<std::uint8_t>(climate.winter));
    for (const std::uint8_t m : climate.minutes) {
        w.u8(m);
    }
    w.u8(day_night.day);
    w.u8(day_night.night);
    w.u8(static_cast<std::uint8_t>(start));
    w.i32(max_population);
    w.u8(static_cast<std::uint8_t>(diseases));
    w.u8(static_cast<std::uint8_t>(fires));
    w.u8(static_cast<std::uint8_t>(raiders));
    w.u8(static_cast<std::uint8_t>(wildlife));
    w.u8(versus ? 1 : 0);
    w.u8(pvp ? 1 : 0);
    w.u8(static_cast<std::uint8_t>(victory));
    w.i32(score_years);
    for (const std::uint8_t r : races) {
        w.u8(r);
    }
    w.u8(other_races);
    w.u16(immigrants);
    w.u8(static_cast<std::uint8_t>(fog));
    w.u8(shared_vision ? 1 : 0);
    w.u8(rest ? 1 : 0);
}

bool GameRules::read(BinaryReader& r, GameRules& out) {
    GameRules g;
    std::uint8_t year = 0, winter = 0, start = 0, diseases = 0, fires = 0, raiders = 0, wildlife = 0;
    if (!r.u8(g.climate.seasons) || !r.u8(year) || !r.u8(winter) || !r.u8(g.climate.minutes[0]) ||
        !r.u8(g.climate.minutes[1]) || !r.u8(g.climate.minutes[2]) || !r.u8(g.climate.minutes[3]) ||
        !r.u8(g.day_night.day) || !r.u8(g.day_night.night) || !r.u8(start) || !r.i32(g.max_population) ||
        !r.u8(diseases) || !r.u8(fires) || !r.u8(raiders) || !r.u8(wildlife)) {
        return false;
    }
    constexpr auto kLevels = static_cast<std::uint8_t>(Threat::Count);
    if (diseases >= kLevels || fires >= kLevels || raiders >= kLevels || wildlife >= kLevels) {
        r.fail();
        return false;
    }
    g.diseases = static_cast<Threat>(diseases);
    g.fires = static_cast<Threat>(fires);
    g.raiders = static_cast<Threat>(raiders);
    g.wildlife = static_cast<Threat>(wildlife);
    std::uint8_t versus = 0, pvp = 0, victory = 0;
    if (!r.u8(versus) || !r.u8(pvp) || !r.u8(victory) || !r.i32(g.score_years)) {
        return false;
    }
    if (versus > 1 || pvp > 1 || victory >= static_cast<std::uint8_t>(Victory::Count) || g.score_years < 1 ||
        g.score_years > 100) {
        r.fail();
        return false;
    }
    g.versus = versus != 0;
    g.pvp = pvp != 0;
    g.victory = static_cast<Victory>(victory);
    for (std::uint8_t& race : g.races) {
        if (!r.u8(race) || (race >= 16 && race != kMixedRace)) {
            r.fail();
            return false;
        }
    }
    if (!r.u8(g.other_races) || g.other_races > 100 || !r.u16(g.immigrants)) {
        r.fail();
        return false;
    }
    std::uint8_t fog = 0, shared_vision = 0;
    if (!r.u8(fog) || fog >= static_cast<std::uint8_t>(FogMode::Count) || !r.u8(shared_vision) || shared_vision > 1) {
        r.fail();
        return false;
    }
    g.fog = static_cast<FogMode>(fog);
    g.shared_vision = shared_vision != 0;
    std::uint8_t rest = 0;
    if (!r.u8(rest) || rest > 1) {
        r.fail();
        return false;
    }
    g.rest = rest != 0;
    if (g.climate.seasons == 0 || g.climate.seasons > 0b1111 || year < kMinYearPercent || year > kMaxYearPercent ||
        year % 5 != 0 ||
        winter >= static_cast<std::uint8_t>(Harshness::Count) || start >= static_cast<std::uint8_t>(StartGoods::Count) ||
        g.max_population < kMinPopulationLimit || g.max_population > kMaxPopulationLimit) {
        r.fail();
        return false;
    }
    // Day and night: both or neither.
    if (g.day_night.day > kMaxDayMinutes || g.day_night.night > kMaxDayMinutes ||
        (g.day_night.day != 0) != (g.day_night.night != 0)) {
        r.fail();
        return false;
    }
    g.climate.year = year;
    // Minutes of their own: every enabled season has them and no other does.
    if (g.climate.own_lengths()) {
        for (std::uint8_t s = 0; s < 4; ++s) {
            const bool on = ((g.climate.seasons >> s) & 1u) != 0;
            if (g.climate.minutes[s] > kMaxSeasonMinutes || on != (g.climate.minutes[s] != 0)) {
                r.fail();
                return false;
            }
        }
    }
    g.climate.winter = static_cast<Harshness>(winter);
    g.start = static_cast<StartGoods>(start);
    out = g;
    return true;
}

std::uint32_t year_ticks(std::uint8_t percent) {
    // 12 000 ticks (20 minutes at x1) at 100 %; always a whole number of
    // ticks per day (a year has 120 days; the percent is a multiple of 5).
    return 120u * std::clamp<std::uint32_t>(percent, kMinYearPercent, kMaxYearPercent);
}

std::uint32_t season_spans(const ClimateSettings& c, std::array<SeasonSpan, 4>& out) {
    std::uint32_t n = 0;
    for (std::uint8_t s = 0; s < 4; ++s) {
        if (((c.seasons >> s) & 1u) != 0) {
            out[n++].season = static_cast<Season>(s);
        }
    }
    if (n == 0) {
        out[n++].season = Season::Summer;
    }
    if (c.own_lengths()) {
        for (std::uint32_t i = 0; i < n; ++i) {
            const std::uint32_t minutes = c.minutes[static_cast<std::size_t>(out[i].season)];
            out[i].ticks = std::clamp<std::uint32_t>(minutes, 1, kMaxSeasonMinutes) * kTicksPerMinute;
        }
        return n;
    }
    // Even parts of the year; the last one takes what does not divide.
    const std::uint32_t year = year_ticks(c.year);
    for (std::uint32_t i = 0; i < n; ++i) {
        out[i].ticks = i + 1 < n ? year / n : year - (year / n) * (n - 1);
    }
    return n;
}

std::uint32_t year_ticks(const ClimateSettings& c) {
    std::array<SeasonSpan, 4> spans{};
    const std::uint32_t n = season_spans(c, spans);
    std::uint32_t year = 0;
    for (std::uint32_t i = 0; i < n; ++i) {
        year += spans[i].ticks;
    }
    return year;
}

namespace {

// The season at a tick of the year: its index among the enabled ones and
// how far through it, 0..999.
struct SeasonAt {
    std::array<SeasonSpan, 4> spans{};
    std::uint32_t count = 0;
    std::uint32_t index = 0;
    std::uint32_t progress = 0;
};

SeasonAt season_at(const ClimateSettings& c, std::uint64_t in_year) {
    SeasonAt at;
    at.count = season_spans(c, at.spans);
    std::uint64_t start = 0;
    for (std::uint32_t i = 0; i < at.count; ++i) {
        if (in_year < start + at.spans[i].ticks || i + 1 == at.count) {
            at.index = i;
            at.progress = static_cast<std::uint32_t>(std::min<std::uint64_t>(999, (in_year - start) * 1000 / at.spans[i].ticks));
            break;
        }
        start += at.spans[i].ticks;
    }
    return at;
}

}  // namespace

Calendar calendar(const ClimateSettings& c, std::uint64_t tick) {
    const std::uint64_t year = year_ticks(c);
    const std::uint64_t in_year = tick % year;
    const std::uint64_t month_ticks = year / kMonths;
    const std::uint64_t day_ticks = month_ticks / kDaysPerMonth;
    Calendar cal;
    cal.year = static_cast<std::uint32_t>(tick / year) + 1;
    cal.month = static_cast<std::uint32_t>(in_year / month_ticks) + 1;
    cal.day = static_cast<std::uint32_t>(in_year % month_ticks / day_ticks) + 1;
    const SeasonAt at = season_at(c, in_year);
    cal.season = at.spans[at.index].season;
    cal.season_progress = at.progress;
    return cal;
}

std::int32_t temperature(const ClimateSettings& c, std::uint64_t seed, std::uint64_t tick) {
    const std::uint64_t year = year_ticks(c);
    const SeasonAt at = season_at(c, tick % year);
    std::int32_t t = base_temperature(at.spans[at.index].season, c.winter);
    // The first quarter of a season eases in from the one before.
    if (at.count > 1 && at.progress < 250) {
        const Season before = at.spans[(at.index + at.count - 1) % at.count].season;
        const std::int32_t from = base_temperature(before, c.winter);
        t = from + (t - from) * static_cast<std::int32_t>(at.progress) / 250;
    }
    // A little variation from day to day, the same everywhere.
    const std::uint64_t day = tick / (year / (kMonths * kDaysPerMonth));
    t += static_cast<std::int32_t>(mix(seed ^ (day * 0x9E3779B97F4A7C15ull)) % 7) - 3;
    return t;
}

DayTime day_time(const DayNightSettings& d, std::uint64_t tick) {
    DayTime t;
    if (!d.enabled()) {
        return t;
    }
    const std::uint64_t day = std::uint64_t{d.day} * kTicksPerMinute;
    const std::uint64_t night = std::uint64_t{d.night} * kTicksPerMinute;
    const std::uint64_t at = tick % (day + night);
    t.night = at >= day;
    const std::uint64_t in = t.night ? at - day : at;
    const std::uint64_t length = t.night ? night : day;
    t.progress = static_cast<std::uint32_t>(in * 1000 / length);
    t.ticks_left = static_cast<std::uint32_t>(length - in);
    return t;
}

}  // namespace sc::sim
