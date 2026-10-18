#include "game/new_game_screen.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <vector>

#include <SDL3/SDL_timer.h>

#include "game/minimap.h"
#include "game/ui_host.h"
#include "i18n/translator.h"
#include "sim/command.h"
#include "sim/noise.h"
#include "sim/worldgen.h"

namespace sc {

using i18n::tr;

namespace {

// The preview is made this long after the last change of the form.
constexpr std::uint64_t kPreviewDelayNs = 350'000'000ull;
// What a varied map takes from its seed.
constexpr std::uint64_t kVariedSeed = 0x5641524945440014ull;
// Half the temperature range of a map of one climate.
constexpr std::uint8_t kEvenClimateRange = 12;
// A season of the usual year, in minutes.
constexpr std::uint8_t kUsualSeasonMinutes = 5;
// The usual day, and the usual night, in minutes.
constexpr std::uint8_t kUsualDayMinutes = 5;

std::string percent_text(int v) {
    return tr("newGame.percent", v);
}

}  // namespace

std::uint64_t parse_seed(std::string_view text) {
    if (text.empty() || text.size() > kMaxSeedDigits) {
        return 0;
    }
    std::uint64_t v = 0;
    for (const char c : text) {
        if (c < '0' || c > '9') {
            return 0;
        }
        v = v * 10 + static_cast<std::uint64_t>(c - '0');
    }
    return v;
}

std::uint64_t random_seed() {
    // splitmix64 over the high-resolution clock: fine for picking a map.
    std::uint64_t z = SDL_GetPerformanceCounter() + 0x9E3779B97F4A7C15ull;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    z ^= z >> 31;
    return 1 + z % 999'999'999ull;
}

const char* map_size_text_key(sim::MapSize size) {
    static constexpr const char* kKeys[] = {"newGame.size.small", "newGame.size.medium", "newGame.size.large",
                                            "newGame.size.huge",  "newGame.size.giant",  "newGame.size.colossal"};
    static_assert(std::size(kKeys) == static_cast<std::size_t>(sim::MapSize::Count));
    return kKeys[std::min<std::size_t>(static_cast<std::size_t>(size), std::size(kKeys) - 1)];
}


// --- Varied ------------------------------------------------------------------

VariedClimate varied_climate(std::uint64_t seed) {
    const std::uint64_t roll = sim::mix64(seed ^ kVariedSeed) % 100;
    return roll < 22 ? VariedClimate::Cold : roll < 62 ? VariedClimate::Temperate : roll < 82 ? VariedClimate::Warm
                                                                                              : VariedClimate::Mixed;
}

sim::MapSettings varied_map(std::uint64_t seed, sim::MapSize size, int players) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = size;
    s.players = static_cast<std::uint8_t>(std::clamp(players, 1, static_cast<int>(sim::kMaxPlayers)));
    s.relief = sim::Relief::Gentle;
    // The climate: a map of one climate, or from cold to warm.
    static constexpr std::uint8_t kTemperature[] = {50, 100, 150, 100};
    const auto climate = static_cast<std::size_t>(varied_climate(seed));
    s.temperature = kTemperature[climate];
    s.climate_range = varied_climate(seed) == VariedClimate::Mixed ? sim::kMaxClimateRange : kEvenClimateRange;
    // The sea: none, one or two sides, and now and then islands.
    const std::uint64_t roll = sim::mix64(seed ^ kVariedSeed ^ 0x53454100ull) % 100;
    s.sea = roll < 35 ? sim::Sea::None : roll < 62 ? sim::Sea::OneSide : roll < 82 ? sim::Sea::TwoSides
          : roll < 92 ? sim::Sea::Islands : sim::Sea::Archipelago;
    s.islands = static_cast<std::uint8_t>(
        std::clamp(2 + static_cast<int>(roll % 2), 1, sim::worldgen::max_islands_per_town(size, s.players)));
    return s;
}

sim::GameRules varied_rules() {
    sim::GameRules r;
    r.fog = sim::FogMode::None;  // Decision D-PARTIDA-01.
    r.races.fill(sim::kMixedRace);
    // The usual year, said in minutes: four seasons of five.
    r.climate.minutes = {kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes};
    r.day_night = {kUsualDayMinutes, kUsualDayMinutes};
    r.rest = true;
    r.rain = 100;
    return r;
}

// --- The form's state ------------------------------------------------------------

NewGameScreen::~NewGameScreen() {
    stop_preview();
}

void NewGameScreen::close() {
    stop_preview();
    wanted_.reset();
    shown_.reset();
    image_.reset();
}

void NewGameScreen::open(const sim::Content* content, bool multiplayer, const NewGameSettings& remembered) {
    close();
    multiplayer_ = multiplayer;
    content_ = content;
    reset();
    apply(remembered);
    settings_.seed = random_seed();
    seed_text_ = std::to_string(settings_.seed);
    asked_ = Result::None;
    resolve();
}

void NewGameScreen::reset() {
    const sim::MapSize size = map_.size;
    const std::uint8_t players = map_.players;
    custom_ = false;
    map_ = sim::MapSettings{};
    map_.size = size;
    map_.players = players;
    map_.relief = sim::Relief::Gentle;
    map_.islands = 3;
    game_ = varied_rules();
    season_minutes_ = {kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes};
    day_night_on_ = true;
    day_minutes_ = kUsualDayMinutes;
    night_minutes_ = kUsualDayMinutes;
    giants_on_ = true;
    other_races_ = 100;
}

void NewGameScreen::start_from_varied() {
    const std::uint64_t seed = parse_seed(seed_text_);
    map_ = varied_map(seed, map_.size, map_.players);
    game_ = varied_rules();
    season_minutes_ = {kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes};
    day_night_on_ = true;
    day_minutes_ = kUsualDayMinutes;
    night_minutes_ = kUsualDayMinutes;
    giants_on_ = true;
    other_races_ = 100;
    custom_ = true;
}

namespace {

namespace names = new_game_names;
static_assert(std::size(names::kSizes) == static_cast<std::size_t>(sim::MapSize::Count));
static_assert(std::size(names::kSeas) == static_cast<std::size_t>(sim::Sea::Count));
static_assert(std::size(names::kWinters) == static_cast<std::size_t>(sim::Harshness::Count));
static_assert(std::size(names::kStarts) == static_cast<std::size_t>(sim::StartGoods::Count));
static_assert(std::size(names::kFogs) == static_cast<std::size_t>(sim::FogMode::Count));
static_assert(std::size(names::kThreats) == static_cast<std::size_t>(sim::Threat::Count));
static_assert(settings_limits::kMaxIslandsPerTown == sim::kMaxIslandsPerTown);
static_assert(settings_limits::kMaxPlayers == static_cast<int>(sim::kMaxPlayers));
static_assert(settings_limits::kMinPopulation == sim::kMinPopulationLimit);
static_assert(settings_limits::kMaxPopulation == sim::kMaxPopulationLimit);

// The value named `text` in `list`, or `fallback`.
template <class E, std::size_t N>
E named(const std::string_view (&list)[N], std::string_view text, E fallback) {
    for (std::size_t i = 0; i < N; ++i) {
        if (list[i] == text) {
            return static_cast<E>(i);
        }
    }
    return fallback;
}

template <class E, std::size_t N>
std::string name_of(const std::string_view (&list)[N], E value) {
    return std::string(list[std::min<std::size_t>(static_cast<std::size_t>(value), N - 1)]);
}

// A percent of the form: on its steps of 25.
std::uint8_t percent(int v, int min = 0) {
    return static_cast<std::uint8_t>(std::clamp(v / 25 * 25, min, 200));
}

// The usual share of newcomers of another race, percent.
constexpr int kUsualOtherRaces = 20;

}  // namespace

void NewGameScreen::apply(const NewGameSettings& n) {
    custom_ = n.mode == names::kModes[1];
    map_.size = named(names::kSizes, n.size, map_.size);
    map_.players = static_cast<std::uint8_t>(std::clamp(n.players, 1, static_cast<int>(sim::kMaxPlayers)));
    map_.temperature = percent(n.temperature);
    map_.humidity = percent(n.humidity);
    map_.climate_range = n.climate == names::kClimates[0] ? kEvenClimateRange : sim::kMaxClimateRange;
    map_.rivers = percent(n.rivers);
    map_.lakes = percent(n.lakes);
    map_.forests = percent(n.forests);
    map_.resources = percent(n.resources);
    map_.relief = percent(n.relief);
    map_.landforms = percent(n.landforms);
    giants_on_ = n.giants_on;
    map_.giants = percent(n.giants);
    map_.sea = named(names::kSeas, n.sea, map_.sea);
    map_.islands = static_cast<std::uint8_t>(std::clamp(n.islands, 1, static_cast<int>(sim::kMaxIslandsPerTown)));
    map_.biomes = 0;
    game_.immigrants = 0;
    if (content_ != nullptr) {
        // The biomes and races that still exist; none left means all.
        for (const std::string& id : n.biomes) {
            if (const int b = content_->flora.find_biome(id); b >= 0 && b < 64) {
                map_.biomes |= std::uint64_t{1} << b;
            }
        }
        if (n.race == names::kMixedRace) {
            game_.races.fill(sim::kMixedRace);
        }
        for (std::size_t r = 0; r < content_->races.size() && r < 16; ++r) {
            if (content_->races[r].id == n.race) {
                game_.races.fill(static_cast<std::uint8_t>(r));
            }
            if (std::find(n.immigrants.begin(), n.immigrants.end(), content_->races[r].id) != n.immigrants.end()) {
                game_.immigrants = static_cast<std::uint16_t>(game_.immigrants | (1u << r));
            }
        }
    }
    if (n.seasons >= 1 && n.seasons <= 0b1111) {
        game_.climate.seasons = static_cast<std::uint8_t>(n.seasons);
    }
    for (std::size_t i = 0; i < 4; ++i) {
        season_minutes_[i] = std::clamp(n.season_minutes[i], 1, static_cast<int>(sim::kMaxSeasonMinutes));
    }
    game_.rest = n.rest;
    game_.rain = static_cast<std::uint8_t>(percent(n.rain));
    day_night_on_ = n.day_night;
    day_minutes_ = std::clamp(n.day_minutes, 1, static_cast<int>(sim::kMaxDayMinutes));
    night_minutes_ = std::clamp(n.night_minutes, 1, static_cast<int>(sim::kMaxDayMinutes));
    game_.climate.winter = named(names::kWinters, n.winter, game_.climate.winter);
    game_.start = named(names::kStarts, n.start, game_.start);
    game_.diseases = named(names::kThreats, n.diseases, game_.diseases);
    game_.fires = named(names::kThreats, n.fires, game_.fires);
    game_.raiders = named(names::kThreats, n.raiders, game_.raiders);
    game_.wildlife = named(names::kThreats, n.wildlife, game_.wildlife);
    other_races_ = percent(n.other_races);
    // On the slider's steps.
    game_.max_population = std::clamp(n.max_population / 50 * 50, sim::kMinPopulationLimit, sim::kMaxPopulationLimit);
    game_.fog = named(names::kFogs, n.fog, game_.fog);
    game_.shared_vision = n.shared_vision;
}

NewGameSettings NewGameScreen::remembered() const {
    NewGameSettings n;
    n.mode = std::string(names::kModes[custom_ ? 1 : 0]);
    n.size = name_of(names::kSizes, map_.size);
    n.players = map_.players;
    n.temperature = map_.temperature;
    n.humidity = map_.humidity;
    n.climate = std::string(names::kClimates[map_.climate_range >= sim::kMaxClimateRange ? 1 : 0]);
    n.rivers = map_.rivers;
    n.lakes = map_.lakes;
    n.forests = map_.forests;
    n.resources = map_.resources;
    n.relief = map_.relief;
    n.landforms = map_.landforms;
    n.giants_on = giants_on_;
    n.giants = map_.giants;
    n.sea = name_of(names::kSeas, map_.sea);
    n.islands = map_.islands;
    if (content_ != nullptr) {
        for (std::size_t b = 0; b < content_->flora.biomes.size() && b < 64 && map_.biomes != 0; ++b) {
            if (((map_.biomes >> b) & 1u) != 0) {
                n.biomes.push_back(content_->flora.biomes[b].id);
            }
        }
        const std::uint8_t race = game_.races[0];
        if (race == sim::kMixedRace) {
            n.race = std::string(names::kMixedRace);
        } else if (race < content_->races.size()) {
            n.race = content_->races[race].id;
        }
        for (std::size_t r = 0; r < content_->races.size() && r < 16 && game_.immigrants != 0; ++r) {
            if (((game_.immigrants >> r) & 1u) != 0) {
                n.immigrants.push_back(content_->races[r].id);
            }
        }
    }
    n.seasons = game_.climate.seasons;
    n.season_minutes = season_minutes_;
    n.rest = game_.rest;
    n.rain = game_.rain;
    n.day_night = day_night_on_;
    n.day_minutes = day_minutes_;
    n.night_minutes = night_minutes_;
    n.winter = name_of(names::kWinters, game_.climate.winter);
    n.start = name_of(names::kStarts, game_.start);
    n.diseases = name_of(names::kThreats, game_.diseases);
    n.fires = name_of(names::kThreats, game_.fires);
    n.raiders = name_of(names::kThreats, game_.raiders);
    n.wildlife = name_of(names::kThreats, game_.wildlife);
    n.other_races = other_races_;
    n.max_population = game_.max_population;
    n.fog = name_of(names::kFogs, game_.fog);
    n.shared_vision = game_.shared_vision;
    return n;
}

void NewGameScreen::resolve() {
    const std::uint64_t typed = parse_seed(seed_text_);
    const std::uint64_t seed = typed != 0 ? typed : settings_.seed;
    if (!custom_) {
        settings_ = varied_map(seed, map_.size, map_.players);
        rules_ = varied_rules();
        return;
    }
    settings_ = map_;
    settings_.seed = seed;
    settings_.islands = static_cast<std::uint8_t>(
        std::clamp<int>(map_.islands, 1, sim::worldgen::max_islands_per_town(map_.size, map_.players)));
    if (!giants_on_) {
        settings_.giants = 0;
    }
    rules_ = game_;
    // The year: the minutes of the seasons it has.
    rules_.climate.year = sim::YearLength::Normal;
    for (std::size_t i = 0; i < 4; ++i) {
        const bool on = ((rules_.climate.seasons >> i) & 1u) != 0;
        rules_.climate.minutes[i] = on ? static_cast<std::uint8_t>(season_minutes_[i]) : std::uint8_t{0};
    }
    rules_.day_night = day_night_on_ ? sim::DayNightSettings{static_cast<std::uint8_t>(day_minutes_),
                                                             static_cast<std::uint8_t>(night_minutes_)}
                                     : sim::DayNightSettings{};
    rules_.other_races = static_cast<std::uint8_t>(std::clamp(kUsualOtherRaces * other_races_ / 100, 0, 100));
}

// --- The preview ---------------------------------------------------------------------

void NewGameScreen::stop_preview() {
    cancel_ = true;
    if (worker_.joinable()) {
        worker_.join();
    }
    cancel_ = false;
    working_ = false;
    const std::lock_guard lock(result_mutex_);
    result_.reset();
}

std::optional<std::vector<std::uint8_t>> NewGameScreen::take_preview() {
    std::optional<std::vector<std::uint8_t>> out = std::move(image_);
    image_.reset();
    return out;
}

void NewGameScreen::update_preview(std::uint64_t now_ns) {
    // A finished picture?
    {
        const std::lock_guard lock(result_mutex_);
        if (result_) {
            image_ = std::move(result_->rgba);
            shown_giants_ = result_->giants;
            shown_sea_sides_ = result_->sea_sides;
            shown_ = wanted_;
            result_.reset();
        }
    }
    const bool possible = content_ != nullptr && parse_seed(seed_text_) != 0 && settings_.size <= kLargestPreview;
    if (!possible) {
        if (wanted_) {
            stop_preview();
            wanted_.reset();
            shown_.reset();
        }
        return;
    }
    if (!wanted_ || !(*wanted_ == settings_)) {
        // Changed: whatever was being made is of no use.
        stop_preview();
        wanted_ = settings_;
        changed_ns_ = now_ns;
        return;
    }
    if (working_ || (shown_ && *shown_ == *wanted_) || now_ns - changed_ns_ < kPreviewDelayNs) {
        return;
    }
    if (worker_.joinable()) {
        worker_.join();
    }
    working_ = true;
    worker_ = std::thread([this, settings = *wanted_, content = content_] {
        const std::optional<sim::MapData> map =
            sim::generate_map(settings, *content, [this](sim::GenStage, int) { return !cancel_.load(); });
        if (map.has_value() && !cancel_) {
            PreviewResult r;
            r.rgba = minimap::render(*map);
            for (const sim::MapFeature& f : map->features) {
                r.giants += f.type == sim::FeatureType::Tree && f.species < content->flora.species.size() &&
                                    content->flora.species[f.species].giant_biome >= 0
                                ? 1
                                : 0;
            }
            // The sides where the sea is: most of that edge is sea.
            const std::uint16_t sea = map->sea_levels.empty() ? std::uint16_t{0} : map->sea_levels[0];
            const std::int32_t n = map->size;
            const auto salt = [&](std::int32_t x, std::int32_t z) {
                const std::uint16_t w = map->water[static_cast<std::size_t>(z) * static_cast<std::size_t>(n) + static_cast<std::size_t>(x)];
                return sea != 0 && w == sea;
            };
            int count[4] = {0, 0, 0, 0};
            for (std::int32_t i = 0; i < n; i += 8) {
                count[0] += salt(i, 2) ? 1 : 0;
                count[1] += salt(i, n - 3) ? 1 : 0;
                count[2] += salt(2, i) ? 1 : 0;
                count[3] += salt(n - 3, i) ? 1 : 0;
            }
            for (int side = 0; side < 4; ++side) {
                if (count[side] * 2 > n / 8) {
                    r.sea_sides = static_cast<std::uint8_t>(r.sea_sides | (1u << side));
                }
            }
            const std::lock_guard lock(result_mutex_);
            result_ = std::move(r);
        }
        working_ = false;
    });
}

std::string NewGameScreen::summary() const {
    // "Temperate map, coast to the east, 3 giant trees".
    static constexpr const char* kClimateKeys[] = {"newGame.summary.cold", "newGame.summary.temperate",
                                                   "newGame.summary.warm", "newGame.summary.mixed"};
    const bool mixed = settings_.climate_range >= sim::kMaxClimateRange;
    const std::size_t climate = mixed ? 3 : settings_.temperature < 75 ? 0 : settings_.temperature > 125 ? 2 : 1;
    std::string text = tr(kClimateKeys[climate]);
    const bool have_picture = shown_ && *shown_ == settings_;
    switch (settings_.sea) {
        case sim::Sea::None: text += ", " + tr("newGame.summary.noSea"); break;
        case sim::Sea::Islands: text += ", " + tr("newGame.summary.islands"); break;
        case sim::Sea::Archipelago: text += ", " + tr("newGame.summary.archipelago"); break;
        default:
            if (have_picture && shown_sea_sides_ != 0) {
                static constexpr const char* kSides[] = {"newGame.summary.north", "newGame.summary.south",
                                                         "newGame.summary.west", "newGame.summary.east"};
                std::string sides;
                for (int side = 0; side < 4; ++side) {
                    if (((shown_sea_sides_ >> side) & 1u) != 0) {
                        sides += (sides.empty() ? "" : tr("newGame.summary.and")) + tr(kSides[side]);
                    }
                }
                text += ", " + tr("newGame.summary.coast", sides);
            } else {
                text += ", " + tr(settings_.sea == sim::Sea::OneSide ? "newGame.summary.oneSide" : "newGame.summary.twoSides");
            }
            break;
    }
    if (have_picture) {
        text += ", " + i18n::tr_n("newGame.summary.giants", shown_giants_, shown_giants_);
    }
    return text;
}

// --- The rows (phase 126: an RmlUi menu panel) -------------------------------------------

namespace {

// Check boxes with their names, two to a row. `set(i, value)` is called when
// box i changes.
void check_grid(ThingRows& out, std::size_t count, const std::function<std::string(std::size_t)>& name,
                const std::string& tip, const std::function<bool(std::size_t)>& get,
                const std::function<void(std::size_t, bool)>& set) {
    std::vector<RowButton> pair;
    for (std::size_t i = 0; i < count; ++i) {
        const bool on = get(i);
        RowButton b = out.button(name(i), tip, row_run([set, i, on] { set(i, !on); }), true, on);
        b.icon = on ? "icon-check" : "icon-minus";
        pair.push_back(std::move(b));
        if (pair.size() == 2 || i + 1 == count) {
            out.buttons(std::move(pair));
            out.rows.back().cls = "checks";
            pair.clear();
        }
    }
}

}  // namespace

std::string NewGameScreen::preview_rml() const {
    if (shown_.has_value()) {
        // Dimmer while a newer one is on its way.
        const bool current = *shown_ == settings_;
        return std::string("<div class=\"preview\" tip=\"") + rml_escape(tr("newGame.preview.tooltip")) +
               "\"><img src=\"/live/preview\" class=\"" + (current ? "now" : "old") + "\"/></div>";
    }
    const char* key = settings_.size > kLargestPreview ? "newGame.preview.tooBig"
                      : parse_seed(seed_text_) == 0    ? "newGame.preview.noSeed"
                                                       : "newGame.preview.making";
    return "<div class=\"preview\"><p>" + rml_escape(tr(key)) + "</p></div>";
}

void NewGameScreen::custom_rows(ThingRows& out) {
    static const sim::Flora kNoFlora;
    const sim::Flora& flora = content_ != nullptr ? content_->flora : kNoFlora;
    const std::size_t biome_count = std::min<std::size_t>(flora.biomes.size(), 64);
    const std::uint64_t all_biomes = biome_count >= 64 ? ~std::uint64_t{0} : (std::uint64_t{1} << biome_count) - 1;

    out.line(tr("newGame.group.climate"), WinRow::Kind::Section);
    const auto percent_row = [&](const char* key, std::uint8_t* value, int min, bool enabled = true) {
        const std::string base = std::string("newGame.") + key;
        row_slide(out, tr(base) + ": " + percent_text(*value), tr(base + ".tooltip"), *value, min, 200, 25, enabled,
                  [value, min](int v) { *value = percent(v, min); });
    };
    percent_row("temperature", &map_.temperature, 0);
    percent_row("humidity", &map_.humidity, 0);
    row_pick(out, tr("newGame.climate"), tr("newGame.climate.tooltip"), {tr("newGame.climate.even"), tr("newGame.climate.mixed")},
             map_.climate_range >= sim::kMaxClimateRange ? 1 : 0, true,
             [this](int i) { map_.climate_range = i == 1 ? sim::kMaxClimateRange : kEvenClimateRange; });
    // The biomes: at least one. All checked is "all" (0), so new biomes of a
    // mod are in too.
    out.line(tr("newGame.biomes")).tip = tr("newGame.biomes.tooltip");
    const std::uint64_t mask = map_.biomes == 0 ? all_biomes : map_.biomes & all_biomes;
    check_grid(
        out, biome_count, [&flora](std::size_t i) { return tr(flora.biomes[i].name_key); }, tr("newGame.biomes.tooltip"),
        [mask](std::size_t i) { return ((mask >> i) & 1u) != 0; },
        [this, mask, all_biomes](std::size_t i, bool on) {
            std::uint64_t next = on ? mask | (std::uint64_t{1} << i) : mask & ~(std::uint64_t{1} << i);
            if (next == 0) {
                next = std::uint64_t{1} << i;  // The last one stays.
            }
            map_.biomes = next == all_biomes ? 0 : next;
        });

    out.line(tr("newGame.group.land"), WinRow::Kind::Section);
    // The sea: none, along one or two sides, or around islands.
    row_pick(out, tr("newGame.sea"), tr("newGame.sea.tooltip"),
             {tr("newGame.sea.none"), tr("newGame.sea.oneSide"), tr("newGame.sea.twoSides"), tr("newGame.sea.islands"),
              tr("newGame.sea.archipelago")},
             static_cast<int>(map_.sea), true, [this](int i) { map_.sea = static_cast<sim::Sea>(i); });
    {
        // Islands per town (phase 22), on an archipelago.
        const bool archipelago = map_.sea == sim::Sea::Archipelago;
        const int most = sim::worldgen::max_islands_per_town(map_.size, map_.players);
        std::vector<std::string> counts;
        for (int k = 1; k <= most; ++k) {
            counts.push_back(i18n::tr_n("newGame.islands.value", k * map_.players, k));
        }
        row_pick(out, tr("newGame.islands"), tr(archipelago ? "newGame.islands.tooltip" : "newGame.islands.disabledTooltip"),
                 counts, std::clamp<int>(map_.islands, 1, std::max(1, most)) - 1, archipelago,
                 [this](int i) { map_.islands = static_cast<std::uint8_t>(i + 1); });
    }
    percent_row("relief", &map_.relief, 0);
    percent_row("landforms", &map_.landforms, 0);
    percent_row("rivers", &map_.rivers, 0);
    percent_row("lakes", &map_.lakes, 0);
    percent_row("forests", &map_.forests, 0);
    percent_row("resources", &map_.resources, 0);
    row_tick(out, tr("newGame.giantsOn"), tr("newGame.giantsOn.tooltip"), giants_on_, true, [this](bool v) { giants_on_ = v; });
    percent_row("giants", &map_.giants, 0, giants_on_);
    rules_rows(out);
}

void NewGameScreen::rules_rows(ThingRows& out) {
    static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                   "hud.season.winter"};
    const auto minutes = [](int m) { return tr("newGame.minutes", m); };
    out.line(tr("newGame.group.year"), WinRow::Kind::Section);
    // Each season by itself; at least one.
    out.line(tr("newGame.seasons")).tip = tr("newGame.seasons.tooltip");
    const std::uint8_t seasons = game_.climate.seasons;
    check_grid(
        out, 4, [](std::size_t i) { return tr(kSeasonKeys[i]); }, tr("newGame.seasons.tooltip"),
        [seasons](std::size_t i) { return ((seasons >> i) & 1u) != 0; },
        [this](std::size_t i, bool on) {
            const auto bit = static_cast<std::uint8_t>(1u << i);
            const auto next = static_cast<std::uint8_t>(on ? game_.climate.seasons | bit : game_.climate.seasons & ~bit);
            game_.climate.seasons = next == 0 ? bit : next;  // The last one stays.
        });
    // A bar per season it has, in minutes; the year is their sum.
    int year_minutes = 0;
    for (std::size_t i = 0; i < 4; ++i) {
        if (((seasons >> i) & 1u) == 0) {
            continue;
        }
        int* value = &season_minutes_[i];
        row_slide(out, tr("newGame.seasonLength", tr(kSeasonKeys[i])) + ": " + minutes(*value), tr("newGame.seasonLength.tooltip"),
                  *value, 1, sim::kMaxSeasonMinutes, 1, true, [value](int v) { *value = v; });
        year_minutes += season_minutes_[i];
    }
    out.stepper(tr("newGame.year"), RowButton{}, RowButton{});
    out.rows.back().detail = minutes(year_minutes);
    out.rows.back().tip = tr("newGame.year.tooltip");
    out.rows.back().cls = "wide";
    row_pick(out, tr("newGame.winter"), tr("newGame.winter.tooltip"),
             {tr("newGame.winter.mild"), tr("newGame.winter.normal"), tr("newGame.winter.harsh")},
             static_cast<int>(game_.climate.winter), (seasons & 0b1000) != 0,
             [this](int i) { game_.climate.winter = static_cast<sim::Harshness>(i); });
    // Phase 97: how much it rains.
    row_slide(out, tr("newGame.rain") + ": " + (game_.rain == 0 ? tr("newGame.rain.never") : tr("newGame.percent", game_.rain)),
              tr("newGame.rain.tooltip"), game_.rain, 0, sim::kMaxRain, 25, true,
              [this](int v) { game_.rain = static_cast<std::uint8_t>(percent(v)); });
    row_tick(out, tr("newGame.dayNight"), tr("newGame.dayNight.tooltip"), day_night_on_, true, [this](bool v) { day_night_on_ = v; });
    if (day_night_on_) {
        row_slide(out, tr("newGame.dayLength") + ": " + minutes(day_minutes_), tr("newGame.dayLength.tooltip"), day_minutes_, 1,
                  sim::kMaxDayMinutes, 1, true, [this](int v) { day_minutes_ = v; });
        row_slide(out, tr("newGame.nightLength") + ": " + minutes(night_minutes_), tr("newGame.dayLength.tooltip"), night_minutes_,
                  1, sim::kMaxDayMinutes, 1, true, [this](int v) { night_minutes_ = v; });
    }

    out.line(tr("newGame.group.game"), WinRow::Kind::Section);
    row_tick(out, tr("newGame.rest"), tr("newGame.rest.tooltip"), game_.rest, true, [this](bool v) { game_.rest = v; });
    row_pick(out, tr("newGame.start"), tr("newGame.start.tooltip"),
             {tr("newGame.start.scarce"), tr("newGame.start.normal"), tr("newGame.start.plenty")}, static_cast<int>(game_.start),
             true, [this](int i) { game_.start = static_cast<sim::StartGoods>(i); });
    const std::vector<std::string> threats = {tr("newGame.threat.none"), tr("newGame.threat.low"), tr("newGame.threat.medium"),
                                              tr("newGame.threat.high"), tr("newGame.threat.brutal")};
    struct ThreatRow {
        const char* key;
        sim::Threat* value;
    };
    for (const ThreatRow& t : {ThreatRow{"diseases", &game_.diseases}, ThreatRow{"fires", &game_.fires},
                               ThreatRow{"raiders", &game_.raiders}, ThreatRow{"wildlife", &game_.wildlife}}) {
        const std::string base = std::string("newGame.") + t.key;
        sim::Threat* value = t.value;
        row_pick(out, tr(base), tr(base + ".tooltip"), threats, static_cast<int>(*t.value), true,
                 [value](int i) { *value = static_cast<sim::Threat>(i); });
    }
    row_slide(out, tr("newGame.maxPopulation") + ": " + tr("newGame.maxPopulation.value", game_.max_population),
              tr("newGame.maxPopulation.tooltip"), game_.max_population, sim::kMinPopulationLimit, sim::kMaxPopulationLimit, 50, true,
              [this](int v) { game_.max_population = std::clamp(v, sim::kMinPopulationLimit, sim::kMaxPopulationLimit); });
    // Phase 32: the fog of war, and whether allies share what they see.
    row_pick(out, tr("newGame.fog"), tr("newGame.fog.tooltip"),
             {tr("newGame.fog.none"), tr("newGame.fog.static"), tr("newGame.fog.dynamic"), tr("newGame.fog.revealed")},
             static_cast<int>(game_.fog), true, [this](int i) { game_.fog = static_cast<sim::FogMode>(i); });
    row_pick(out, tr("newGame.sharedVision"), tr("newGame.sharedVision.tooltip"),
             {tr("newGame.sharedVision.off"), tr("newGame.sharedVision.on")}, game_.shared_vision ? 1 : 0,
             game_.fog != sim::FogMode::None, [this](int i) { game_.shared_vision = i == 1; });

    // The people (phase 19).
    if (content_ != nullptr && !content_->races.empty()) {
        out.line(tr("newGame.group.people"), WinRow::Kind::Section);
        const std::size_t race_count = std::min<std::size_t>(content_->races.size(), 16);
        std::vector<std::string> options;
        for (std::size_t r = 0; r < race_count; ++r) {
            options.push_back(tr(content_->races[r].name_key));
        }
        options.push_back(tr("newGame.race.mixed"));
        const std::uint8_t current = game_.races[0];
        const int count = static_cast<int>(race_count);
        row_pick(out, tr("newGame.race"), tr("newGame.race.tooltip"), options,
                 current == sim::kMixedRace || current >= race_count ? count : current, true, [this, count](int i) {
                     game_.races.fill(i >= count ? sim::kMixedRace : static_cast<std::uint8_t>(i));
                 });
        row_slide(out, tr("newGame.otherRaces") + ": " + tr("newGame.otherRaces.value", other_races_, kUsualOtherRaces * other_races_ / 100),
                  tr("newGame.otherRaces.tooltip"), other_races_, 0, 200, 25, true, [this](int v) { other_races_ = percent(v); });
        // The races that may come as newcomers. All checked is "all" (0).
        out.line(tr("newGame.immigrants")).tip = tr("newGame.immigrants.tooltip");
        const auto all = static_cast<std::uint16_t>(race_count >= 16 ? 0xFFFFu : (1u << race_count) - 1u);
        const auto mask = static_cast<std::uint16_t>(game_.immigrants == 0 ? all : game_.immigrants & all);
        check_grid(
            out, race_count, [this](std::size_t i) { return tr(content_->races[i].name_key); }, tr("newGame.immigrants.tooltip"),
            [mask](std::size_t i) { return ((mask >> i) & 1u) != 0; },
            [this, mask, all](std::size_t i, bool on) {
                auto next = static_cast<std::uint16_t>(on ? mask | (1u << i) : mask & ~(1u << i));
                if (next == 0) {
                    next = static_cast<std::uint16_t>(1u << i);  // The last one stays.
                }
                game_.immigrants = next == all ? std::uint16_t{0} : next;
            });
    }
}

ThingRows NewGameScreen::rows() {
    ThingRows out;
    out.line(tr("newGame.title"), WinRow::Kind::Title);
    // The seed: digits only, and only what fits in 64 bits.
    out.line(tr("newGame.seed"), WinRow::Kind::Dim).tip = tr("newGame.seed.tooltip");
    WinRow& seed = out.line(seed_text_, WinRow::Kind::Input);
    seed.max = static_cast<int>(kMaxSeedDigits);
    seed.tip = tr("newGame.seed.tooltip");
    seed.act = out.add_act([this](GameSession*, const RowInput& in, RowEffects&) {
        std::string digits;
        for (const char c : in.text) {
            if (c >= '0' && c <= '9' && !(c == '0' && digits.empty()) && digits.size() < kMaxSeedDigits) {
                digits += c;
            }
        }
        while (!digits.empty() && parse_seed(digits) == 0) {
            digits.pop_back();
        }
        seed_text_ = digits;
        if (in.enter && parse_seed(seed_text_) != 0) {
            asked_ = Result::Generate;
        }
    });
    out.buttons({out.button(tr("newGame.seed.random"), tr("newGame.seed.random.tooltip"),
                            row_run([this] { seed_text_ = std::to_string(random_seed()); }))});
    {
        std::vector<std::string> options;
        for (std::uint8_t i = 0; i < static_cast<std::uint8_t>(sim::MapSize::Count); ++i) {
            const auto size = static_cast<sim::MapSize>(i);
            options.push_back(tr(map_size_text_key(size), sim::map_cells(size)));
        }
        // The biggest sizes warn about time and memory.
        row_pick(out, tr("newGame.size"),
                 map_.size >= sim::MapSize::Giant ? tr(std::string(map_size_text_key(map_.size)) + ".tooltip") : tr("newGame.size.tooltip"),
                 options, static_cast<int>(map_.size), true, [this](int i) { map_.size = static_cast<sim::MapSize>(i); });
    }
    row_slide(out, tr("newGame.players") + ": " + i18n::tr_n("newGame.players.value", map_.players), tr("newGame.players.tooltip"),
              map_.players, 1, 12, 1, true, [this](int v) { map_.players = static_cast<std::uint8_t>(std::clamp(v, 1, 12)); });
    // The kind of map: varied, or everything by hand.
    row_pick(out, tr("newGame.mode"), tr(custom_ ? "newGame.mode.custom.tooltip" : "newGame.mode.varied.tooltip"),
             {tr("newGame.mode.varied"), tr("newGame.mode.custom")}, custom_ ? 1 : 0, true, [this](int i) { custom_ = i == 1; });
    out.line(preview_rml(), WinRow::Kind::Raw);
    out.line(summary(), WinRow::Kind::Paragraph).cls = "center";
    if (custom_) {
        custom_rows(out);
    }
    const std::uint64_t seed_value = parse_seed(seed_text_);
    std::vector<RowButton> buttons;
    if (custom_) {
        buttons.push_back(out.button(tr("newGame.fromVaried"), tr("newGame.fromVaried.tooltip"), row_run([this] {
                                         start_from_varied();
                                         resolve();
                                     }),
                                     seed_value != 0));
    }
    buttons.push_back(out.button(tr("newGame.back"), tr("newGame.back.tooltip"), row_run([this] { asked_ = Result::Back; })));
    buttons.push_back(out.button(tr(multiplayer_ ? "newGame.openLobby" : "newGame.generate"),
                                 tr(seed_value != 0 ? "newGame.generate.tooltip" : "newGame.generate.noSeed.tooltip"),
                                 row_run([this] { asked_ = Result::Generate; }), seed_value != 0, true));
    out.buttons(std::move(buttons));
    out.rows.back().cls = "big";
    return out;
}

NewGameScreen::Result NewGameScreen::frame(ui::Context& ctx, UiHost& host, bool modal) {
    resolve();
    update_preview(ctx.now_ns());
    host.menu("new_game", rows(), 720.0f);
    return frame(ctx, modal);
}

NewGameScreen::Result NewGameScreen::frame(ui::Context& ctx, bool modal) {
    resolve();
    update_preview(ctx.now_ns());
    if (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        asked_ = Result::Back;
    }
    if (!modal && parse_seed(seed_text_) != 0 && (ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_KP_ENTER))) {
        asked_ = Result::Generate;
    }
    Result result = asked_;
    asked_ = Result::None;
    if (result == Result::Generate && parse_seed(seed_text_) == 0) {
        result = Result::None;
    }
    if (result != Result::None) {
        resolve();
        stop_preview();
    }
    return result;
}

}  // namespace sc
