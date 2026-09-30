#include "game/new_game_screen.h"

#include <algorithm>
#include <cmath>
#include <vector>

#include <SDL3/SDL_timer.h>

#include "i18n/translator.h"
#include "sim/command.h"
#include "sim/worldgen.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kRowHeight = 44.0f;
constexpr float kRowGap = 10.0f;

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

std::vector<std::string> amount_options() {
    return {tr("newGame.amount.low"), tr("newGame.amount.normal"), tr("newGame.amount.high")};
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

// Seasons presets: which seasons the year has.
namespace {
constexpr std::uint8_t kSeasonPresets[] = {0b1111, 0b0111, 0b0010, 0b1000, 0b1010, 0b0001};
constexpr const char* kSeasonPresetKeys[] = {"newGame.seasons.four",   "newGame.seasons.noWinter",
                                             "newGame.seasons.summer", "newGame.seasons.winter",
                                             "newGame.seasons.summerWinter", "newGame.seasons.spring"};
}  // namespace

const char* map_size_text_key(sim::MapSize size) {
    static constexpr const char* kKeys[] = {"newGame.size.small", "newGame.size.medium", "newGame.size.large",
                                            "newGame.size.huge",  "newGame.size.giant",  "newGame.size.colossal"};
    static_assert(std::size(kKeys) == static_cast<std::size_t>(sim::MapSize::Count));
    return kKeys[std::min<std::size_t>(static_cast<std::size_t>(size), std::size(kKeys) - 1)];
}

void NewGameScreen::open(const sim::Content* content, bool multiplayer, const NewGameSettings& remembered) {
    multiplayer_ = multiplayer;
    content_ = content;
    reset();
    apply(remembered);
    settings_.seed = random_seed();
    seed_text_ = std::to_string(settings_.seed);
    seed_focused_ = false;
}

void NewGameScreen::reset() {
    const std::uint64_t seed = settings_.seed;
    settings_ = sim::MapSettings{};
    settings_.seed = seed;
    rules_ = sim::GameRules{};
    rules_.fog = sim::FogMode::Static;  // The form's default (decision D-3202).
}

namespace {

namespace names = new_game_names;
static_assert(std::size(names::kSizes) == static_cast<std::size_t>(sim::MapSize::Count));
static_assert(std::size(names::kAmounts) == static_cast<std::size_t>(sim::Amount::Count));
static_assert(std::size(names::kReliefs) == static_cast<std::size_t>(sim::Relief::Count));
static_assert(std::size(names::kSeas) == static_cast<std::size_t>(sim::Sea::Count));
static_assert(std::size(names::kYears) == static_cast<std::size_t>(sim::YearLength::Count));
static_assert(std::size(names::kWinters) == static_cast<std::size_t>(sim::Harshness::Count));
static_assert(std::size(names::kStarts) == static_cast<std::size_t>(sim::StartGoods::Count));
static_assert(std::size(names::kFogs) == static_cast<std::size_t>(sim::FogMode::Count));
static_assert(std::size(names::kGenerators) == static_cast<std::size_t>(sim::MapGenerator::Count));
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

}  // namespace

void NewGameScreen::apply(const NewGameSettings& n) {
    settings_.size = named(names::kSizes, n.size, settings_.size);
    settings_.water = named(names::kAmounts, n.water, settings_.water);
    settings_.forests = named(names::kAmounts, n.forests, settings_.forests);
    settings_.resources = named(names::kAmounts, n.resources, settings_.resources);
    settings_.relief = named(names::kReliefs, n.relief, settings_.relief);
    settings_.sea = named(names::kSeas, n.sea, settings_.sea);
    settings_.landforms = named(names::kAmounts, n.landforms, settings_.landforms);
    settings_.generator = named(names::kGenerators, n.generator, settings_.generator);
    settings_.players = static_cast<std::uint8_t>(std::clamp(n.players, 1, static_cast<int>(sim::kMaxPlayers)));
    settings_.islands = static_cast<std::uint8_t>(std::clamp(n.islands, 1, static_cast<int>(sim::kMaxIslandsPerTown)));
    if (content_ != nullptr) {
        if (const int t = content_->flora.find_map_type(n.map_type); t >= 0) {
            settings_.map_type = static_cast<std::uint8_t>(t);
        }
        if (const int b = content_->flora.find_biome(n.biome); b >= 0) {
            settings_.biome = static_cast<std::uint8_t>(b);
        }
        if (n.race == names::kMixedRace) {
            rules_.races.fill(sim::kMixedRace);
        } else {
            for (std::size_t r = 0; r < content_->races.size(); ++r) {
                if (content_->races[r].id == n.race) {
                    rules_.races.fill(static_cast<std::uint8_t>(r));
                }
            }
        }
    }
    // Only the seasons the form offers.
    if (std::find(std::begin(kSeasonPresets), std::end(kSeasonPresets), n.seasons) != std::end(kSeasonPresets)) {
        rules_.climate.seasons = static_cast<std::uint8_t>(n.seasons);
    }
    rules_.climate.year = named(names::kYears, n.year, rules_.climate.year);
    rules_.climate.winter = named(names::kWinters, n.winter, rules_.climate.winter);
    rules_.start = named(names::kStarts, n.start, rules_.start);
    rules_.diseases = named(names::kThreats, n.diseases, rules_.diseases);
    rules_.fires = named(names::kThreats, n.fires, rules_.fires);
    rules_.raiders = named(names::kThreats, n.raiders, rules_.raiders);
    rules_.wildlife = named(names::kThreats, n.wildlife, rules_.wildlife);
    rules_.other_races = static_cast<std::uint8_t>(std::clamp(n.other_races, 0, 100));
    // On the slider's steps.
    rules_.max_population = std::clamp(n.max_population / 50 * 50, sim::kMinPopulationLimit, sim::kMaxPopulationLimit);
    rules_.fog = named(names::kFogs, n.fog, rules_.fog);
    rules_.shared_vision = n.shared_vision;
}

NewGameSettings NewGameScreen::remembered() const {
    NewGameSettings n;
    n.size = name_of(names::kSizes, settings_.size);
    n.water = name_of(names::kAmounts, settings_.water);
    n.forests = name_of(names::kAmounts, settings_.forests);
    n.resources = name_of(names::kAmounts, settings_.resources);
    n.relief = name_of(names::kReliefs, settings_.relief);
    n.sea = name_of(names::kSeas, settings_.sea);
    n.landforms = name_of(names::kAmounts, settings_.landforms);
    n.generator = name_of(names::kGenerators, settings_.generator);
    n.players = settings_.players;
    n.islands = settings_.islands;
    if (content_ != nullptr) {
        if (settings_.map_type < content_->flora.map_types.size()) {
            n.map_type = content_->flora.map_types[settings_.map_type].id;
        }
        if (settings_.biome < content_->flora.biomes.size()) {
            n.biome = content_->flora.biomes[settings_.biome].id;
        }
        const std::uint8_t race = rules_.races[0];
        if (race == sim::kMixedRace) {
            n.race = std::string(names::kMixedRace);
        } else if (race < content_->races.size()) {
            n.race = content_->races[race].id;
        }
    }
    n.seasons = rules_.climate.seasons;
    n.year = name_of(names::kYears, rules_.climate.year);
    n.winter = name_of(names::kWinters, rules_.climate.winter);
    n.start = name_of(names::kStarts, rules_.start);
    n.diseases = name_of(names::kThreats, rules_.diseases);
    n.fires = name_of(names::kThreats, rules_.fires);
    n.raiders = name_of(names::kThreats, rules_.raiders);
    n.wildlife = name_of(names::kThreats, rules_.wildlife);
    n.other_races = rules_.other_races;
    n.max_population = rules_.max_population;
    n.fog = name_of(names::kFogs, rules_.fog);
    n.shared_vision = rules_.shared_vision;
    return n;
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

void NewGameScreen::rules_rows(ui::Context& ctx, float x, float& y, float cw) {
    {
        std::vector<std::string> options;
        int index = 0;
        for (std::size_t i = 0; i < std::size(kSeasonPresets); ++i) {
            options.push_back(tr(kSeasonPresetKeys[i]));
            index = kSeasonPresets[i] == rules_.climate.seasons ? static_cast<int>(i) : index;
        }
        const Row r = row(ctx, x, y, cw, tr("newGame.seasons"), tr("newGame.seasons.tooltip"));
        if (ctx.selector(ctx.id("seasons"), r.control, index, options, tr("newGame.seasons.tooltip"))) {
            rules_.climate.seasons = kSeasonPresets[index];
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.year.short"), tr("newGame.year.normal"),
                                                  tr("newGame.year.long")};
        int index = static_cast<int>(rules_.climate.year);
        const Row r = row(ctx, x, y, cw, tr("newGame.year"), tr("newGame.year.tooltip"));
        if (ctx.selector(ctx.id("year"), r.control, index, options, tr("newGame.year.tooltip"))) {
            rules_.climate.year = static_cast<sim::YearLength>(index);
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.winter.mild"), tr("newGame.winter.normal"),
                                                  tr("newGame.winter.harsh")};
        int index = static_cast<int>(rules_.climate.winter);
        const bool has_winter = (rules_.climate.seasons & 0b1000) != 0;
        const Row r = row(ctx, x, y, cw, tr("newGame.winter"), tr("newGame.winter.tooltip"));
        if (ctx.selector(ctx.id("winter"), r.control, index, options, tr("newGame.winter.tooltip"), has_winter)) {
            rules_.climate.winter = static_cast<sim::Harshness>(index);
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.start.scarce"), tr("newGame.start.normal"),
                                                  tr("newGame.start.plenty")};
        int index = static_cast<int>(rules_.start);
        const Row r = row(ctx, x, y, cw, tr("newGame.start"), tr("newGame.start.tooltip"));
        if (ctx.selector(ctx.id("start_goods"), r.control, index, options, tr("newGame.start.tooltip"))) {
            rules_.start = static_cast<sim::StartGoods>(index);
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.threat.none"), tr("newGame.threat.low"),
                                                  tr("newGame.threat.medium"), tr("newGame.threat.high"),
                                                  tr("newGame.threat.brutal")};
        int index = static_cast<int>(rules_.diseases);
        const Row r = row(ctx, x, y, cw, tr("newGame.diseases"), tr("newGame.diseases.tooltip"));
        if (ctx.selector(ctx.id("diseases"), r.control, index, options, tr("newGame.diseases.tooltip"))) {
            rules_.diseases = static_cast<sim::Threat>(index);
        }
        index = static_cast<int>(rules_.fires);
        const Row f = row(ctx, x, y, cw, tr("newGame.fires"), tr("newGame.fires.tooltip"));
        if (ctx.selector(ctx.id("fires"), f.control, index, options, tr("newGame.fires.tooltip"))) {
            rules_.fires = static_cast<sim::Threat>(index);
        }
        index = static_cast<int>(rules_.raiders);
        const Row rr = row(ctx, x, y, cw, tr("newGame.raiders"), tr("newGame.raiders.tooltip"));
        if (ctx.selector(ctx.id("raiders"), rr.control, index, options, tr("newGame.raiders.tooltip"))) {
            rules_.raiders = static_cast<sim::Threat>(index);
        }
        index = static_cast<int>(rules_.wildlife);
        const Row wr = row(ctx, x, y, cw, tr("newGame.wildlife"), tr("newGame.wildlife.tooltip"));
        if (ctx.selector(ctx.id("wildlife"), wr.control, index, options, tr("newGame.wildlife.tooltip"))) {
            rules_.wildlife = static_cast<sim::Threat>(index);
        }
    }
    // The people (phase 19).
    if (content_ != nullptr && !content_->races.empty()) {
        std::vector<std::string> options;
        for (const sim::RaceDef& r : content_->races) {
            options.push_back(tr(r.name_key));
        }
        options.push_back(tr("newGame.race.mixed"));
        const std::uint8_t current = rules_.races[0];
        int index = current == sim::kMixedRace || current >= content_->races.size() ? static_cast<int>(content_->races.size())
                                                                                     : current;
        const Row r = row(ctx, x, y, cw, tr("newGame.race"), tr("newGame.race.tooltip"));
        if (ctx.selector(ctx.id("race"), r.control, index, options, tr("newGame.race.tooltip"))) {
            const auto race = index >= static_cast<int>(content_->races.size()) ? sim::kMixedRace
                                                                                 : static_cast<std::uint8_t>(index);
            rules_.races.fill(race);
        }
        const std::vector<std::string> others = {tr("newGame.otherRaces.none"), tr("newGame.otherRaces.few"),
                                                 tr("newGame.otherRaces.many")};
        int o = rules_.other_races == 0 ? 0 : rules_.other_races < 40 ? 1 : 2;
        const Row orow = row(ctx, x, y, cw, tr("newGame.otherRaces"), tr("newGame.otherRaces.tooltip"));
        if (ctx.selector(ctx.id("other_races"), orow.control, o, others, tr("newGame.otherRaces.tooltip"))) {
            static constexpr std::uint8_t kShare[] = {0, 20, 50};
            rules_.other_races = kShare[o];
        }
    }
    {
        int limit = rules_.max_population;
        const Row r = row(ctx, x, y, cw, tr("newGame.maxPopulation"), tr("newGame.maxPopulation.tooltip"));
        if (ctx.slider(ctx.id("max_population"), r.control, limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit, 50,
                       [](int v) { return tr("newGame.maxPopulation.value", v); }, tr("newGame.maxPopulation.tooltip"))) {
            rules_.max_population = std::clamp(limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit);
        }
    }
    // Phase 32: the fog of war, and whether allies share what they see.
    {
        const std::vector<std::string> options = {tr("newGame.fog.none"), tr("newGame.fog.static"),
                                                  tr("newGame.fog.dynamic")};
        int index = static_cast<int>(rules_.fog);
        const Row r = row(ctx, x, y, cw, tr("newGame.fog"), tr("newGame.fog.tooltip"));
        if (ctx.selector(ctx.id("fog"), r.control, index, options, tr("newGame.fog.tooltip"))) {
            rules_.fog = static_cast<sim::FogMode>(index);
        }
        const std::vector<std::string> shared = {tr("newGame.sharedVision.off"), tr("newGame.sharedVision.on")};
        int on = rules_.shared_vision ? 1 : 0;
        const Row s = row(ctx, x, y, cw, tr("newGame.sharedVision"), tr("newGame.sharedVision.tooltip"));
        if (ctx.selector(ctx.id("shared_vision"), s.control, on, shared, tr("newGame.sharedVision.tooltip"),
                         rules_.fog != sim::FogMode::None)) {
            rules_.shared_vision = on == 1;
        }
    }
}

NewGameScreen::Result NewGameScreen::frame(ui::Context& ctx, bool modal) {
    const float margin = ctx.s(16.0f);
    const float pad = ctx.s(24.0f);
    const float w = std::min(ctx.s(680.0f), ctx.width() - 2 * margin);
    const ui::TextStyle title_style = ctx.style(ctx.theme().title, ui::FontRole::Bold);
    const float title_h = ctx.text().line_height(title_style);
    const bool wide = w - 2 * pad >= ctx.s(480.0f);
    const float row_h = wide ? ctx.s(kRowHeight + kRowGap)
                             : ctx.text().line_height(ctx.style(ctx.theme().body)) + ctx.s(4.0f + kRowHeight + kRowGap);
    constexpr int kRows = 25;
    const float button_h = ctx.s(48.0f);
    const float content_h = title_h + pad + kRows * row_h + pad + button_h;
    const float h = content_h + 2 * pad;

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
        // Phase 39: a different way of making the map, not an option of one.
        std::vector<std::string> options;
        for (const std::string_view name : names::kGenerators) {
            options.push_back(tr("newGame.generator." + std::string(name)));
        }
        int index = static_cast<int>(settings_.generator);
        const std::string tip = tr("newGame.generator." + std::string(names::kGenerators[index]) + ".tooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.generator"), tip);
        if (ctx.selector(ctx.id("generator"), r.control, index, options, tip)) {
            settings_.generator = static_cast<sim::MapGenerator>(index);
        }
    }
    {
        std::vector<std::string> options;
        for (std::uint8_t i = 0; i < static_cast<std::uint8_t>(sim::MapSize::Count); ++i) {
            const auto size = static_cast<sim::MapSize>(i);
            options.push_back(tr(map_size_text_key(size), sim::map_cells(size)));
        }
        int index = static_cast<int>(settings_.size);
        // The biggest sizes warn about time and memory.
        const std::string tip = settings_.size >= sim::MapSize::Giant
                                    ? tr(std::string(map_size_text_key(settings_.size)) + ".tooltip")
                                    : tr("newGame.size.tooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.size"), tip);
        if (ctx.selector(ctx.id("size"), r.control, index, options, tip)) {
            settings_.size = static_cast<sim::MapSize>(index);
        }
    }
    {
        std::vector<std::string> options;
        static const sim::Flora kNoFlora;
        const sim::Flora& flora = content_ != nullptr ? content_->flora : kNoFlora;
        for (const sim::MapTypeDef& t : flora.map_types) {
            options.push_back(tr(t.name_key));
        }
        if (options.empty()) {
            options.push_back("-");
        }
        int index = static_cast<int>(settings_.map_type);
        const std::string tip = settings_.map_type < flora.map_types.size()
                                    ? tr(flora.map_types[settings_.map_type].name_key + ".tooltip")
                                    : std::string{};
        const Row r = row(ctx, x, y, cw, tr("newGame.mapType"), tip);
        if (ctx.selector(ctx.id("map_type"), r.control, index, options, tip)) {
            settings_.map_type = static_cast<std::uint8_t>(index);
        }
    }
    {
        // Islands per town (phase 22), for a map type with islands.
        static const sim::Flora kNoFlora;
        const sim::Flora& flora = content_ != nullptr ? content_->flora : kNoFlora;
        const bool islands = settings_.map_type < flora.map_types.size() && flora.map_types[settings_.map_type].islands;
        const int most = sim::worldgen::max_islands_per_town(settings_.size, settings_.players);
        settings_.islands = static_cast<std::uint8_t>(std::clamp<int>(settings_.islands, 1, most));
        std::vector<std::string> options;
        for (int k = 1; k <= most; ++k) {
            options.push_back(i18n::tr_n("newGame.islands.value", k * settings_.players, k));
        }
        int index = settings_.islands - 1;
        const std::string tip = tr(islands ? "newGame.islands.tooltip" : "newGame.islands.disabledTooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.islands"), tip);
        if (ctx.selector(ctx.id("islands"), r.control, index, options, tip, islands)) {
            settings_.islands = static_cast<std::uint8_t>(index + 1);
        }
        // The sea (phase 26), for the other map types.
        const std::vector<std::string> seas = {tr("newGame.sea.none"), tr("newGame.sea.sometimes"), tr("newGame.sea.always")};
        int sea = static_cast<int>(settings_.sea);
        const std::string sea_tip = tr(islands ? "newGame.sea.disabledTooltip" : "newGame.sea.tooltip");
        const Row sr = row(ctx, x, y, cw, tr("newGame.sea"), sea_tip);
        if (ctx.selector(ctx.id("sea"), sr.control, sea, seas, sea_tip, !islands)) {
            settings_.sea = static_cast<sim::Sea>(sea);
        }
    }
    {
        std::vector<std::string> options;
        static const sim::Flora kNoFlora;
        const sim::Flora& flora = content_ != nullptr ? content_->flora : kNoFlora;
        for (const sim::BiomeDef& b : flora.biomes) {
            options.push_back(tr(b.name_key));
        }
        if (options.empty()) {
            options.push_back("-");
        }
        int index = static_cast<int>(settings_.biome);
        // The biome matters for map types without their own mix of biomes.
        const bool single = settings_.map_type < flora.map_types.size() && flora.map_types[settings_.map_type].biomes.empty();
        const std::string tip = tr(single ? "newGame.biome.tooltip" : "newGame.biome.disabledTooltip");
        const Row r = row(ctx, x, y, cw, tr("newGame.biome"), tip);
        if (ctx.selector(ctx.id("biome"), r.control, index, options, tip, single)) {
            settings_.biome = static_cast<std::uint8_t>(index);
        }
    }
    struct AmountRow {
        const char* key;
        sim::Amount* value;
    };
    const AmountRow amounts[] = {
        {"water", &settings_.water}, {"forests", &settings_.forests}, {"resources", &settings_.resources}};
    const std::vector<std::string> amount_names = amount_options();
    for (const AmountRow& a : amounts) {
        const std::string base = std::string("newGame.") + a.key;
        int index = static_cast<int>(*a.value);
        const Row r = row(ctx, x, y, cw, tr(base), tr(base + ".tooltip"));
        if (ctx.selector(ctx.id(a.key), r.control, index, amount_names, tr(base + ".tooltip"))) {
            *a.value = static_cast<sim::Amount>(index);
        }
    }
    {
        const std::vector<std::string> options = {tr("newGame.relief.low"), tr("newGame.relief.gentle"),
                                                  tr("newGame.relief.mountainous")};
        int index = static_cast<int>(settings_.relief);
        const Row r = row(ctx, x, y, cw, tr("newGame.relief"), tr("newGame.relief.tooltip"));
        if (ctx.selector(ctx.id("relief"), r.control, index, options, tr("newGame.relief.tooltip"))) {
            settings_.relief = static_cast<sim::Relief>(index);
        }
    }
    {
        // Plateaus, valleys, ranges and canyons (phase 27).
        int index = static_cast<int>(settings_.landforms);
        const Row r = row(ctx, x, y, cw, tr("newGame.landforms"), tr("newGame.landforms.tooltip"));
        if (ctx.selector(ctx.id("landforms"), r.control, index, amount_names, tr("newGame.landforms.tooltip"))) {
            settings_.landforms = static_cast<sim::Amount>(index);
        }
    }
    {
        int players = settings_.players;
        const Row r = row(ctx, x, y, cw, tr("newGame.players"), tr("newGame.players.tooltip"));
        if (ctx.slider(ctx.id("players"), r.control, players, 1, 12, 1,
                       [](int v) { return i18n::tr_n("newGame.players.value", v); }, tr("newGame.players.tooltip"))) {
            settings_.players = static_cast<std::uint8_t>(std::clamp(players, 1, 12));
        }
    }

    rules_rows(ctx, x, y, cw);

    y += pad - ctx.s(kRowGap);
    const float gap = ctx.s(12.0f);
    const float bw = std::min(ctx.s(200.0f), (cw - 2 * gap) / 3.0f);
    const ui::Rect generate{x + cw - bw, y, bw, button_h};
    const ui::Rect back{generate.x - gap - bw, y, bw, button_h};
    const ui::Rect defaults{x, y, bw, button_h};
    if (ctx.button(ctx.id("defaults"), defaults, tr("newGame.defaults"), tr("newGame.defaults.tooltip"))) {
        reset();
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
        settings_.seed = seed;
        seed_focused_ = false;
        result = Result::Generate;
    }
    ctx.end_scroll(box.bottom() - top + margin);
    return result;
}

}  // namespace sc
