#include "game/new_game_screen.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <vector>

#include <SDL3/SDL_timer.h>

#include "game/minimap.h"
#include "i18n/translator.h"
#include "sim/command.h"
#include "sim/noise.h"
#include "sim/worldgen.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kRowHeight = 44.0f;
constexpr float kRowGap = 10.0f;
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

// Digit typed with this key, or -1.
int digit_for(SDL_Scancode key) {
    if (key >= SDL_SCANCODE_1 && key <= SDL_SCANCODE_9) {
        return 1 + (key - SDL_SCANCODE_1);
    }
    if (key >= SDL_SCANCODE_KP_1 && key <= SDL_SCANCODE_KP_9) {
        return 1 + (key - SDL_SCANCODE_KP_1);
    }
    if (key == SDL_SCANCODE_0 || key == SDL_SCANCODE_KP_0) {
        return 0;
    }
    return -1;
}

struct Row {
    ui::Rect label;
    ui::Rect control;
};

Row row(ui::Context& ctx, float x, float& y, float width, std::string_view label, std::string_view tooltip) {
    const float h = ctx.s(kRowHeight);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    Row r;
    if (width >= ctx.s(480.0f)) {
        const float label_w = std::round(width * 0.40f);
        r.label = {x, y, label_w - ctx.s(12.0f), h};
        r.control = {x + label_w, y, width - label_w, h};
        y += h + ctx.s(kRowGap);
    } else {
        const float lh = ctx.text().line_height(st);
        r.label = {x, y, width, lh};
        r.control = {x, y + lh + ctx.s(4.0f), width, h};
        y += lh + ctx.s(4.0f) + h + ctx.s(kRowGap);
    }
    ctx.tooltip_area(ctx.id(std::string(label) + "#row"), {x, r.label.y, width, r.control.bottom() - r.label.y}, tooltip);
    ctx.label(r.label, label, st, ctx.theme().text);
    return r;
}


// A heading between groups of rows.
void heading(ui::Context& ctx, float x, float& y, float width, std::string_view text) {
    const ui::TextStyle st = ctx.style(ctx.theme().body, ui::FontRole::Bold);
    const float h = ctx.text().line_height(st);
    y += ctx.s(6.0f);
    ctx.label({x, y, width, h}, text, st, ctx.theme().accent);
    y += h + ctx.s(kRowGap);
}

// Check boxes with their names, in columns. `set(i, value)` is called when
// box i changes.
template <typename Get, typename Set>
void check_grid(ui::Context& ctx, float x, float& y, float width, std::string_view id, std::size_t count,
                const std::function<std::string(std::size_t)>& name, std::string_view tooltip, Get get, Set set) {
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const int columns = width >= ctx.s(480.0f) ? 2 : 1;
    const float cell_w = width / static_cast<float>(columns);
    const float cell_h = ctx.s(34.0f);
    const float box = ctx.s(24.0f);
    for (std::size_t i = 0; i < count; ++i) {
        const auto column = static_cast<int>(i % static_cast<std::size_t>(columns));
        const ui::Rect cell{x + static_cast<float>(column) * cell_w, y, cell_w - ctx.s(8.0f), cell_h};
        bool value = get(i);
        if (ctx.checkbox(ctx.id(std::string(id) + "#" + std::to_string(i)), cell, value, tooltip)) {
            set(i, value);
        }
        ctx.label({cell.x + box + ctx.s(10.0f), cell.y, cell.w - box - ctx.s(10.0f), cell.h}, name(i), st, ctx.theme().text);
        if (column == columns - 1 || i + 1 == count) {
            y += cell_h + ctx.s(4.0f);
        }
    }
    y += ctx.s(kRowGap - 4.0f);
}

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
    r.fog = sim::FogMode::Static;  // Decision D-3202.
    // The usual year, said in minutes: four seasons of five.
    r.climate.minutes = {kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes, kUsualSeasonMinutes};
    r.day_night = {kUsualDayMinutes, kUsualDayMinutes};
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
    seed_focused_ = false;
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

void NewGameScreen::seed_field(ui::Context& ctx, const ui::Rect& r, bool modal) {
    const float gap = ctx.s(8.0f);
    const float button_w = std::min(ctx.s(130.0f), r.w * 0.4f);
    const ui::Rect box{r.x, r.y, r.w - button_w - gap, r.h};
    const ui::Rect random{box.right() + gap, r.y, button_w, r.h};

    const ui::Input& in = ctx.input();
    const bool inside = in.mouse_x >= box.x && in.mouse_x < box.right() && in.mouse_y >= box.y && in.mouse_y < box.bottom();
    if (!modal && in.mouse_pressed) {
        seed_focused_ = inside;
    }
    if (seed_focused_ && !modal) {
        for (const SDL_Scancode key : in.keys) {
            const int digit = digit_for(key);
            if (digit >= 0 && seed_text_.size() < kMaxSeedDigits) {
                // Leading zeros add nothing.
                if (!(digit == 0 && seed_text_.empty())) {
                    seed_text_ += static_cast<char>('0' + digit);
                }
            } else if (key == SDL_SCANCODE_BACKSPACE && !seed_text_.empty()) {
                seed_text_.pop_back();
            } else if (key == SDL_SCANCODE_DELETE) {
                seed_text_.clear();
            }
        }
    }
    // Keep only what fits in 64 bits.
    while (!seed_text_.empty() && parse_seed(seed_text_) == 0) {
        seed_text_.pop_back();
    }

    const ui::Theme& theme = ctx.theme();
    ctx.draw().rect(box, theme.button_active);
    ctx.draw().rect_outline(box, seed_focused_ ? theme.accent : theme.panel_border,
                            std::max(1.0f, std::round(ctx.s(seed_focused_ ? 2.0f : 1.0f))));
    ctx.tooltip_area(ctx.id("seed_box"), box, tr("newGame.seed.tooltip"));
    const ui::TextStyle st = ctx.style(theme.body);
    const float pad = ctx.s(10.0f);
    const ui::Rect text_rect{box.x + pad, box.y, box.w - 2 * pad, box.h};
    if (seed_text_.empty() && !seed_focused_) {
        ctx.label(text_rect, tr("newGame.seed.placeholder"), st, theme.text_disabled);
    } else {
        ctx.label(text_rect, seed_text_, st, theme.text);
    }
    if (seed_focused_ && (ctx.now_ns() / 500'000'000ull) % 2 == 0) {
        const float caret_x = std::min(text_rect.right(), text_rect.x + ctx.text().measure(st, seed_text_) + ctx.s(1.0f));
        const float lh = ctx.text().line_height(st);
        ctx.draw().rect({std::round(caret_x), std::round(box.y + (box.h - lh) * 0.5f), std::max(1.0f, ctx.s(2.0f)), lh},
                        theme.accent);
    }
    if (ctx.button(ctx.id("seed_random"), random, tr("newGame.seed.random"), tr("newGame.seed.random.tooltip"))) {
        seed_text_ = std::to_string(random_seed());
        seed_focused_ = false;
    }
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

void NewGameScreen::preview_panel(ui::Context& ctx, float x, float& y, float cw) {
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float lh = ctx.text().line_height(st);
    const float side = std::min(cw, ctx.s(256.0f));
    const ui::Rect picture{std::round(x + (cw - side) * 0.5f), y, side, side};
    ctx.draw().rect(picture, ctx.theme().button);
    const bool have_picture = shown_.has_value();
    if (have_picture) {
        // Dimmer while a newer one is on its way.
        const bool current = *shown_ == settings_;
        ctx.draw().picture(picture, kPreviewImageId, 0.0f, 0.0f, 1.0f, 1.0f, ui::Color::rgb(current ? 0xFFFFFF : 0x909090));
    } else {
        const char* key = settings_.size > kLargestPreview   ? "newGame.preview.tooBig"
                          : parse_seed(seed_text_) == 0       ? "newGame.preview.noSeed"
                                                              : "newGame.preview.making";
        const float pad = ctx.s(12.0f);
        ctx.paragraph({picture.x + pad, picture.y + pad, picture.w - 2 * pad, picture.h - 2 * pad}, tr(key), st,
                      ctx.theme().text_dim, ui::Align::Center);
    }
    ctx.draw().rect_outline(picture, ctx.theme().panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
    ctx.tooltip_area(ctx.id("preview"), picture, tr("newGame.preview.tooltip"));
    y += side + ctx.s(8.0f);
    const std::string text = summary();
    const float h = std::max(lh, ctx.paragraph_height(cw, text, st));
    ctx.paragraph({x, y, cw, h}, text, st, ctx.theme().text, ui::Align::Center);
    y += h + ctx.s(kRowGap);
}

// --- The rows ---------------------------------------------------------------------------

void NewGameScreen::custom_rows(ui::Context& ctx, float x, float& y, float cw) {
    static const sim::Flora kNoFlora;
    const sim::Flora& flora = content_ != nullptr ? content_->flora : kNoFlora;
    const std::size_t biome_count = std::min<std::size_t>(flora.biomes.size(), 64);
    const std::uint64_t all_biomes = biome_count >= 64 ? ~std::uint64_t{0} : (std::uint64_t{1} << biome_count) - 1;

    heading(ctx, x, y, cw, tr("newGame.group.climate"));
    struct PercentRow {
        const char* key;
        std::uint8_t* value;
        int min;
    };
    const auto percent_row = [&](const PercentRow& p, bool enabled = true) {
        const std::string base = std::string("newGame.") + p.key;
        int v = *p.value;
        const Row r = row(ctx, x, y, cw, tr(base), tr(base + ".tooltip"));
        if (ctx.slider(ctx.id(p.key), r.control, v, p.min, 200, 25, percent_text, tr(base + ".tooltip"), enabled)) {
            *p.value = percent(v, p.min);
        }
    };
    percent_row({"temperature", &map_.temperature, 0});
    percent_row({"humidity", &map_.humidity, 0});
    {
        const std::vector<std::string> options = {tr("newGame.climate.even"), tr("newGame.climate.mixed")};
        int index = map_.climate_range >= sim::kMaxClimateRange ? 1 : 0;
        const Row r = row(ctx, x, y, cw, tr("newGame.climate"), tr("newGame.climate.tooltip"));
        if (ctx.selector(ctx.id("climate"), r.control, index, options, tr("newGame.climate.tooltip"))) {
            map_.climate_range = index == 1 ? sim::kMaxClimateRange : kEvenClimateRange;
        }
    }
    // The biomes: at least one. All checked is "all" (0), so new biomes of a
    // mod are in too.
    {
        const ui::TextStyle st = ctx.style(ctx.theme().body);
        const float lh = ctx.text().line_height(st);
        ctx.label({x, y, cw, lh}, tr("newGame.biomes"), st, ctx.theme().text);
        ctx.tooltip_area(ctx.id("biomes#label"), {x, y, cw, lh}, tr("newGame.biomes.tooltip"));
        y += lh + ctx.s(6.0f);
        const std::uint64_t mask = map_.biomes == 0 ? all_biomes : map_.biomes & all_biomes;
        check_grid(
            ctx, x, y, cw, "biome", biome_count, [&](std::size_t i) { return tr(flora.biomes[i].name_key); },
            tr("newGame.biomes.tooltip"), [&](std::size_t i) { return ((mask >> i) & 1u) != 0; },
            [&](std::size_t i, bool on) {
                std::uint64_t next = on ? mask | (std::uint64_t{1} << i) : mask & ~(std::uint64_t{1} << i);
                if (next == 0) {
                    next = std::uint64_t{1} << i;  // The last one stays.
                }
                map_.biomes = next == all_biomes ? 0 : next;
            });
    }

    heading(ctx, x, y, cw, tr("newGame.group.land"));
    {
        // The sea: none, along one or two sides, or around islands.
        const std::vector<std::string> options = {tr("newGame.sea.none"), tr("newGame.sea.oneSide"), tr("newGame.sea.twoSides"),
                                                  tr("newGame.sea.islands"), tr("newGame.sea.archipelago")};
        int index = static_cast<int>(map_.sea);
        const Row r = row(ctx, x, y, cw, tr("newGame.sea"), tr("newGame.sea.tooltip"));
        if (ctx.selector(ctx.id("sea"), r.control, index, options, tr("newGame.sea.tooltip"))) {
            map_.sea = static_cast<sim::Sea>(index);
        }
        // Islands per town (phase 22), on an archipelago.
        const bool archipelago = map_.sea == sim::Sea::Archipelago;
        const int most = sim::worldgen::max_islands_per_town(map_.size, map_.players);
        std::vector<std::string> counts;
        for (int k = 1; k <= most; ++k) {
            counts.push_back(i18n::tr_n("newGame.islands.value", k * map_.players, k));
        }
        int islands = std::clamp<int>(map_.islands, 1, most) - 1;
        const std::string tip = tr(archipelago ? "newGame.islands.tooltip" : "newGame.islands.disabledTooltip");
        const Row ir = row(ctx, x, y, cw, tr("newGame.islands"), tip);
        if (ctx.selector(ctx.id("islands"), ir.control, islands, counts, tip, archipelago)) {
            map_.islands = static_cast<std::uint8_t>(islands + 1);
        }
    }
    for (const PercentRow& p : {PercentRow{"relief", &map_.relief, 0}, PercentRow{"landforms", &map_.landforms, 0},
                                PercentRow{"rivers", &map_.rivers, 0}, PercentRow{"lakes", &map_.lakes, 0},
                                PercentRow{"forests", &map_.forests, 0}, PercentRow{"resources", &map_.resources, 0}}) {
        percent_row(p);
    }
    {
        const Row r = row(ctx, x, y, cw, tr("newGame.giantsOn"), tr("newGame.giantsOn.tooltip"));
        (void)ctx.checkbox(ctx.id("giants_on"), r.control, giants_on_, tr("newGame.giantsOn.tooltip"));
        percent_row({"giants", &map_.giants, 0}, giants_on_);
    }
    rules_rows(ctx, x, y, cw);
}

void NewGameScreen::rules_rows(ui::Context& ctx, float x, float& y, float cw) {
    heading(ctx, x, y, cw, tr("newGame.group.year"));
    {
        // Each season by itself; at least one.
        static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                      "hud.season.winter"};
        const ui::TextStyle st = ctx.style(ctx.theme().body);
        const float lh = ctx.text().line_height(st);
        ctx.label({x, y, cw, lh}, tr("newGame.seasons"), st, ctx.theme().text);
        ctx.tooltip_area(ctx.id("seasons#label"), {x, y, cw, lh}, tr("newGame.seasons.tooltip"));
        y += lh + ctx.s(6.0f);
        check_grid(
            ctx, x, y, cw, "season", 4, [&](std::size_t i) { return tr(kSeasonKeys[i]); }, tr("newGame.seasons.tooltip"),
            [&](std::size_t i) { return ((game_.climate.seasons >> i) & 1u) != 0; },
            [&](std::size_t i, bool on) {
                const auto bit = static_cast<std::uint8_t>(1u << i);
                const auto next = static_cast<std::uint8_t>(on ? game_.climate.seasons | bit : game_.climate.seasons & ~bit);
                game_.climate.seasons = next == 0 ? bit : next;  // The last one stays.
            });
    }
    // A bar per season it has, in minutes; the year is their sum.
    int year_minutes = 0;
    for (std::size_t i = 0; i < 4; ++i) {
        static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                      "hud.season.winter"};
        if (((game_.climate.seasons >> i) & 1u) == 0) {
            continue;
        }
        const Row r = row(ctx, x, y, cw, tr("newGame.seasonLength", tr(kSeasonKeys[i])), tr("newGame.seasonLength.tooltip"));
        (void)ctx.slider(ctx.id(std::string("season_minutes") + std::to_string(i)), r.control, season_minutes_[i], 1,
                         sim::kMaxSeasonMinutes, 1, [](int m) { return tr("newGame.minutes", m); },
                         tr("newGame.seasonLength.tooltip"));
        year_minutes += season_minutes_[i];
    }
    {
        const Row r = row(ctx, x, y, cw, tr("newGame.year"), tr("newGame.year.tooltip"));
        ctx.label(r.control, tr("newGame.minutes", year_minutes), ctx.style(ctx.theme().body), ctx.theme().text_dim,
                  ui::Align::Center);
    }
    {
        const std::vector<std::string> options = {tr("newGame.winter.mild"), tr("newGame.winter.normal"),
                                                  tr("newGame.winter.harsh")};
        int index = static_cast<int>(game_.climate.winter);
        const bool has_winter = (game_.climate.seasons & 0b1000) != 0;
        const Row r = row(ctx, x, y, cw, tr("newGame.winter"), tr("newGame.winter.tooltip"));
        if (ctx.selector(ctx.id("winter"), r.control, index, options, tr("newGame.winter.tooltip"), has_winter)) {
            game_.climate.winter = static_cast<sim::Harshness>(index);
        }
    }

    {
        const Row r = row(ctx, x, y, cw, tr("newGame.dayNight"), tr("newGame.dayNight.tooltip"));
        (void)ctx.checkbox(ctx.id("day_night_on"), r.control, day_night_on_, tr("newGame.dayNight.tooltip"));
    }
    if (day_night_on_) {
        const Row d = row(ctx, x, y, cw, tr("newGame.dayLength"), tr("newGame.dayLength.tooltip"));
        (void)ctx.slider(ctx.id("day_minutes"), d.control, day_minutes_, 1, sim::kMaxDayMinutes, 1,
                         [](int m) { return tr("newGame.minutes", m); }, tr("newGame.dayLength.tooltip"));
        const Row n = row(ctx, x, y, cw, tr("newGame.nightLength"), tr("newGame.dayLength.tooltip"));
        (void)ctx.slider(ctx.id("night_minutes"), n.control, night_minutes_, 1, sim::kMaxDayMinutes, 1,
                         [](int m) { return tr("newGame.minutes", m); }, tr("newGame.dayLength.tooltip"));
    }

    heading(ctx, x, y, cw, tr("newGame.group.game"));
    {
        const std::vector<std::string> options = {tr("newGame.start.scarce"), tr("newGame.start.normal"),
                                                  tr("newGame.start.plenty")};
        int index = static_cast<int>(game_.start);
        const Row r = row(ctx, x, y, cw, tr("newGame.start"), tr("newGame.start.tooltip"));
        if (ctx.selector(ctx.id("start_goods"), r.control, index, options, tr("newGame.start.tooltip"))) {
            game_.start = static_cast<sim::StartGoods>(index);
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.threat.none"), tr("newGame.threat.low"),
                                                  tr("newGame.threat.medium"), tr("newGame.threat.high"),
                                                  tr("newGame.threat.brutal")};
        struct ThreatRow {
            const char* key;
            sim::Threat* value;
        };
        for (const ThreatRow& t : {ThreatRow{"diseases", &game_.diseases}, ThreatRow{"fires", &game_.fires},
                                   ThreatRow{"raiders", &game_.raiders}, ThreatRow{"wildlife", &game_.wildlife}}) {
            const std::string base = std::string("newGame.") + t.key;
            int index = static_cast<int>(*t.value);
            const Row r = row(ctx, x, y, cw, tr(base), tr(base + ".tooltip"));
            if (ctx.selector(ctx.id(t.key), r.control, index, options, tr(base + ".tooltip"))) {
                *t.value = static_cast<sim::Threat>(index);
            }
        }
    }
    {
        int limit = game_.max_population;
        const Row r = row(ctx, x, y, cw, tr("newGame.maxPopulation"), tr("newGame.maxPopulation.tooltip"));
        if (ctx.slider(ctx.id("max_population"), r.control, limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit, 50,
                       [](int v) { return tr("newGame.maxPopulation.value", v); }, tr("newGame.maxPopulation.tooltip"))) {
            game_.max_population = std::clamp(limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit);
        }
    }
    // Phase 32: the fog of war, and whether allies share what they see.
    {
        const std::vector<std::string> options = {tr("newGame.fog.none"), tr("newGame.fog.static"),
                                                  tr("newGame.fog.dynamic"),
                                                  tr("newGame.fog.revealed")};
        int index = static_cast<int>(game_.fog);
        const Row r = row(ctx, x, y, cw, tr("newGame.fog"), tr("newGame.fog.tooltip"));
        if (ctx.selector(ctx.id("fog"), r.control, index, options, tr("newGame.fog.tooltip"))) {
            game_.fog = static_cast<sim::FogMode>(index);
        }
        const std::vector<std::string> shared = {tr("newGame.sharedVision.off"), tr("newGame.sharedVision.on")};
        int on = game_.shared_vision ? 1 : 0;
        const Row s = row(ctx, x, y, cw, tr("newGame.sharedVision"), tr("newGame.sharedVision.tooltip"));
        if (ctx.selector(ctx.id("shared_vision"), s.control, on, shared, tr("newGame.sharedVision.tooltip"),
                         game_.fog != sim::FogMode::None)) {
            game_.shared_vision = on == 1;
        }
    }

    // The people (phase 19).
    if (content_ != nullptr && !content_->races.empty()) {
        heading(ctx, x, y, cw, tr("newGame.group.people"));
        const std::size_t race_count = std::min<std::size_t>(content_->races.size(), 16);
        std::vector<std::string> options;
        for (std::size_t r = 0; r < race_count; ++r) {
            options.push_back(tr(content_->races[r].name_key));
        }
        options.push_back(tr("newGame.race.mixed"));
        const std::uint8_t current = game_.races[0];
        int index = current == sim::kMixedRace || current >= race_count ? static_cast<int>(race_count) : current;
        const Row r = row(ctx, x, y, cw, tr("newGame.race"), tr("newGame.race.tooltip"));
        if (ctx.selector(ctx.id("race"), r.control, index, options, tr("newGame.race.tooltip"))) {
            game_.races.fill(index >= static_cast<int>(race_count) ? sim::kMixedRace : static_cast<std::uint8_t>(index));
        }
        {
            int v = other_races_;
            const Row orow = row(ctx, x, y, cw, tr("newGame.otherRaces"), tr("newGame.otherRaces.tooltip"));
            if (ctx.slider(ctx.id("other_races"), orow.control, v, 0, 200, 25,
                           [](int p) { return tr("newGame.otherRaces.value", p, kUsualOtherRaces * p / 100); },
                           tr("newGame.otherRaces.tooltip"))) {
                other_races_ = percent(v);
            }
        }
        // The races that may come as newcomers. All checked is "all" (0).
        const ui::TextStyle st = ctx.style(ctx.theme().body);
        const float lh = ctx.text().line_height(st);
        ctx.label({x, y, cw, lh}, tr("newGame.immigrants"), st, ctx.theme().text);
        ctx.tooltip_area(ctx.id("immigrants#label"), {x, y, cw, lh}, tr("newGame.immigrants.tooltip"));
        y += lh + ctx.s(6.0f);
        const auto all = static_cast<std::uint16_t>(race_count >= 16 ? 0xFFFFu : (1u << race_count) - 1u);
        const auto mask = static_cast<std::uint16_t>(game_.immigrants == 0 ? all : game_.immigrants & all);
        check_grid(
            ctx, x, y, cw, "immigrant", race_count, [&](std::size_t i) { return tr(content_->races[i].name_key); },
            tr("newGame.immigrants.tooltip"), [&](std::size_t i) { return ((mask >> i) & 1u) != 0; },
            [&](std::size_t i, bool on) {
                auto next = static_cast<std::uint16_t>(on ? mask | (1u << i) : mask & ~(1u << i));
                if (next == 0) {
                    next = static_cast<std::uint16_t>(1u << i);  // The last one stays.
                }
                game_.immigrants = next == all ? std::uint16_t{0} : next;
            });
    }
}

NewGameScreen::Result NewGameScreen::frame(ui::Context& ctx, bool modal) {
    const float margin = ctx.s(16.0f);
    const float pad = ctx.s(24.0f);
    const float w = std::min(ctx.s(680.0f), ctx.width() - 2 * margin);
    const ui::TextStyle title_style = ctx.style(ctx.theme().title, ui::FontRole::Bold);
    const float title_h = ctx.text().line_height(title_style);
    const float button_h = ctx.s(48.0f);
    // The panel takes the height the rows had the frame before.
    const float h = last_height_ > 0.0f ? last_height_ : ctx.s(700.0f);

    const ui::Rect viewport{0, 0, ctx.width(), ctx.height()};
    const float top = ctx.begin_scroll(ctx.id("new_game"), viewport);
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round(top + std::max(margin, (ctx.height() - h) * 0.5f)),
                       std::round(w), std::round(h)};
    ctx.panel(box);
    float x = box.x + pad;
    float y = box.y + pad;
    const float cw = box.w - 2 * pad;
    ctx.label({x, y, cw, title_h}, tr("newGame.title"), title_style, ctx.theme().accent);
    y += title_h + pad;

    Result result = Result::None;
    {
        const Row r = row(ctx, x, y, cw, tr("newGame.seed"), tr("newGame.seed.tooltip"));
        seed_field(ctx, r.control, modal);
    }
    {
        std::vector<std::string> options;
        for (std::uint8_t i = 0; i < static_cast<std::uint8_t>(sim::MapSize::Count); ++i) {
            const auto size = static_cast<sim::MapSize>(i);
            options.push_back(tr(map_size_text_key(size), sim::map_cells(size)));
        }
        int index = static_cast<int>(map_.size);
        // The biggest sizes warn about time and memory.
        const std::string tip = map_.size >= sim::MapSize::Giant ? tr(std::string(map_size_text_key(map_.size)) + ".tooltip")
                                                                 : tr("newGame.size.tooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.size"), tip);
        if (ctx.selector(ctx.id("size"), r.control, index, options, tip)) {
            map_.size = static_cast<sim::MapSize>(index);
        }
    }
    {
        int players = map_.players;
        const Row r = row(ctx, x, y, cw, tr("newGame.players"), tr("newGame.players.tooltip"));
        if (ctx.slider(ctx.id("players"), r.control, players, 1, 12, 1,
                       [](int v) { return i18n::tr_n("newGame.players.value", v); }, tr("newGame.players.tooltip"))) {
            map_.players = static_cast<std::uint8_t>(std::clamp(players, 1, 12));
        }
    }
    {
        // The kind of map: varied, or everything by hand.
        const std::vector<std::string> options = {tr("newGame.mode.varied"), tr("newGame.mode.custom")};
        int index = custom_ ? 1 : 0;
        const std::string tip = tr(custom_ ? "newGame.mode.custom.tooltip" : "newGame.mode.varied.tooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.mode"), tip);
        if (ctx.selector(ctx.id("mode"), r.control, index, options, tip)) {
            custom_ = index == 1;
        }
    }
    resolve();
    update_preview(ctx.now_ns());
    preview_panel(ctx, x, y, cw);

    if (custom_) {
        custom_rows(ctx, x, y, cw);
        resolve();
    }

    y += pad - ctx.s(kRowGap);
    const float gap = ctx.s(12.0f);
    const float bw = std::min(ctx.s(200.0f), (cw - 2 * gap) / 3.0f);
    const ui::Rect generate{x + cw - bw, y, bw, button_h};
    const ui::Rect back{generate.x - gap - bw, y, bw, button_h};
    const ui::Rect from_varied{x, y, bw, button_h};
    if (custom_ && ctx.button(ctx.id("from_varied"), from_varied, tr("newGame.fromVaried"), tr("newGame.fromVaried.tooltip"),
                              parse_seed(seed_text_) != 0)) {
        start_from_varied();
        resolve();
    }
    const std::uint64_t seed = parse_seed(seed_text_);
    if (ctx.button(ctx.id("back"), back, tr("newGame.back"), tr("newGame.back.tooltip")) ||
        (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        result = Result::Back;
    }
    const bool can_generate = seed != 0;
    const std::string tip = tr(can_generate ? "newGame.generate.tooltip" : "newGame.generate.noSeed.tooltip");
    const bool enter = !modal && can_generate &&
                       (ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_KP_ENTER));
    if (ctx.button(ctx.id("generate"), generate, tr(multiplayer_ ? "newGame.openLobby" : "newGame.generate"), tip,
                   can_generate, true) ||
        enter) {
        seed_focused_ = false;
        resolve();
        result = Result::Generate;
    }
    y += button_h;
    last_height_ = y + pad - box.y;
    ctx.end_scroll(box.bottom() - top + margin);
    if (result != Result::None) {
        stop_preview();
    }
    return result;
}

}  // namespace sc
