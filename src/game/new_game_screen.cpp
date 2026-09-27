#include "game/new_game_screen.h"

#include <algorithm>
#include <cmath>
#include <vector>

#include <SDL3/SDL_timer.h>

#include "i18n/translator.h"

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

void NewGameScreen::open(const sim::Content* content, bool multiplayer) {
    multiplayer_ = multiplayer;
    content_ = content;
    settings_ = sim::MapSettings{};
    settings_.seed = random_seed();
    seed_text_ = std::to_string(settings_.seed);
    seed_focused_ = false;
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

// Seasons presets: which seasons the year has.
namespace {
constexpr std::uint8_t kSeasonPresets[] = {0b1111, 0b0111, 0b0010, 0b1000, 0b1010, 0b0001};
constexpr const char* kSeasonPresetKeys[] = {"newGame.seasons.four",   "newGame.seasons.noWinter",
                                             "newGame.seasons.summer", "newGame.seasons.winter",
                                             "newGame.seasons.summerWinter", "newGame.seasons.spring"};
}  // namespace

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
        int limit = rules_.max_population;
        const Row r = row(ctx, x, y, cw, tr("newGame.maxPopulation"), tr("newGame.maxPopulation.tooltip"));
        if (ctx.slider(ctx.id("max_population"), r.control, limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit, 50,
                       [](int v) { return tr("newGame.maxPopulation.value", v); }, tr("newGame.maxPopulation.tooltip"))) {
            rules_.max_population = std::clamp(limit, sim::kMinPopulationLimit, sim::kMaxPopulationLimit);
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
    constexpr int kRows = 14;
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
        const std::vector<std::string> options = {
            tr("newGame.size.small", sim::map_cells(sim::MapSize::Small)),
            tr("newGame.size.medium", sim::map_cells(sim::MapSize::Medium)),
            tr("newGame.size.large", sim::map_cells(sim::MapSize::Large)),
            tr("newGame.size.huge", sim::map_cells(sim::MapSize::Huge))};
        int index = static_cast<int>(settings_.size);
        const Row r = row(ctx, x, y, cw, tr("newGame.size"), tr("newGame.size.tooltip"));
        if (ctx.selector(ctx.id("size"), r.control, index, options, tr("newGame.size.tooltip"))) {
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
    const float bw = std::min(ctx.s(220.0f), (cw - gap) * 0.5f);
    const ui::Rect generate{x + cw - bw, y, bw, button_h};
    const ui::Rect back{generate.x - gap - bw, y, bw, button_h};
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
