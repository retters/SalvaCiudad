#include "game/game_hud.h"

#include <algorithm>
#include <cmath>

#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 44.0f;
constexpr float kBuildButtonW = 150.0f;
constexpr float kBuildButtonH = 44.0f;
constexpr float kWindowW = 360.0f;

const char* place_error_key(sim::PlaceError e) {
    switch (e) {
        case sim::PlaceError::None: return "hud.place.ok";
        case sim::PlaceError::UnknownBuilding: return "hud.place.error.unknown";
        case sim::PlaceError::OutsideMap: return "hud.place.error.outside";
        case sim::PlaceError::Water: return "hud.place.error.water";
        case sim::PlaceError::TooSteep: return "hud.place.error.steep";
        case sim::PlaceError::Blocked: return "hud.place.error.blocked";
        case sim::PlaceError::Unique: return "hud.place.error.unique";
        case sim::PlaceError::NotYours: return "hud.place.error.notYours";
        case sim::PlaceError::TooFar: return "hud.place.error.tooFar";
        case sim::PlaceError::TooMany: return "hud.place.error.tooMany";
        case sim::PlaceError::BadSize: return "hud.place.error.badSize";
    }
    return "hud.place.error.unknown";
}

// A thin horizontal bar filled to `fraction`.
void meter(ui::Context& ctx, const ui::Rect& r, float fraction, ui::Color fill) {
    ctx.draw().rect(r, ctx.theme().button_active);
    ctx.draw().rect({r.x, r.y, std::round(r.w * std::clamp(fraction, 0.0f, 1.0f)), r.h}, fill);
    ctx.draw().rect_outline(r, ctx.theme().panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
}

}  // namespace

const char* task_text_key(sim::Task task) {
    switch (task) {
        case sim::Task::Idle: return "task.idle";
        case sim::Task::Wander: return "task.wander";
        case sim::Task::GoEat: return "task.goEat";
        case sim::Task::GoGather: return "task.goGather";
        case sim::Task::Gather: return "task.gather";
        case sim::Task::GoDeliver: return "task.goDeliver";
        case sim::Task::GoFetch: return "task.goFetch";
        case sim::Task::GoSite: return "task.goSite";
        case sim::Task::GoBuild: return "task.goBuild";
        case sim::Task::Build: return "task.build";
        case sim::Task::GoWorkplace: return "task.goWorkplace";
        case sim::Task::Produce: return "task.produce";
        case sim::Task::GoField: return "task.goField";
        case sim::Task::Farm: return "task.farm";
        case sim::Task::GoHunt: return "task.goHunt";
        case sim::Task::Hunt: return "task.hunt";
        case sim::Task::GoFish: return "task.goFish";
        case sim::Task::Fish: return "task.fish";
        case sim::Task::Count: break;
    }
    return "task.idle";
}

GameDate game_date(std::uint64_t tick) {
    GameDate d;
    d.year = static_cast<std::int32_t>(tick / sim::kTicksPerYear) + 1;
    d.month = static_cast<std::int32_t>(tick % sim::kTicksPerYear / sim::kTicksPerMonth) + 1;
    d.day = static_cast<std::int32_t>(tick % sim::kTicksPerMonth / sim::kTicksPerDay) + 1;
    return d;
}

bool GameHud::pressed(const ui::Context& ctx, Action action) const {
    const KeyBindings& b = services_.settings().input.bindings;
    for (const SDL_Scancode k : ctx.input().keys) {
        if (b.matches(action, k)) {
            return true;
        }
    }
    return false;
}

void GameHud::block(GameSession& s, const ui::Rect& r) {
    s.ui().hud_rects.push_back({r.x, r.y, r.w, r.h});
}

std::string GameHud::cost_text(const sim::BuildingDef& def) const {
    const sim::Content* content = services_.content();
    std::string out;
    for (const sim::ResourceAmount& c : def.cost) {
        if (content == nullptr || c.resource >= content->resources.size()) {
            continue;
        }
        if (!out.empty()) {
            out += ", ";
        }
        out += tr("hud.amount", tr(content->resources[c.resource].name_key), c.amount);
    }
    return out.empty() ? tr("hud.cost.free") : out;
}

bool GameHud::frame(ui::Context& ctx, bool blocked) {
    GameSession* s = services_.session();
    if (s == nullptr) {
        return false;
    }
    GameSession::Interaction& ui = s->ui();
    ui.hud_rects.clear();
    const sim::Game& game = s->game();
    // Selections of things that are gone are dropped.
    if (ui.selected_building.valid() && game.buildings().get(ui.selected_building) == nullptr) {
        ui.selected_building = {};
    }
    if (ui.selected_villager.valid() && game.villagers().get(ui.selected_villager) == nullptr) {
        ui.selected_villager = {};
    }

    bool open_menu = false;
    if (!blocked) {
        if (pressed(ctx, Action::GameRotateBuilding) && ui.placing != sim::kNoDef) {
            ui.rotation = static_cast<std::uint8_t>((ui.rotation + 1) & 3u);
        }
        if (ctx.input().key(SDL_SCANCODE_ESCAPE)) {
            if (ui.field_farm.valid()) {
                ui.field_farm = {};
                ui.field_dragging = false;
            } else if (ui.placing != sim::kNoDef) {
                ui.placing = sim::kNoDef;
            } else if (ui.selected_building.valid() || ui.selected_villager.valid()) {
                ui.selected_building = {};
                ui.selected_villager = {};
            } else {
                open_menu = true;
            }
        }
    }

    top_bar(ctx, *s);
    build_bar(ctx, *s);
    if (ui.placing != sim::kNoDef || ui.field_farm.valid()) {
        placement_hint(ctx, *s);
    }
    if (ui.selected_building.valid()) {
        building_window(ctx, *s);
    } else if (ui.selected_villager.valid()) {
        villager_window(ctx, *s);
    }
    return open_menu;
}

void GameHud::top_bar(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const ui::Rect bar{0, 0, ctx.width(), std::round(ctx.s(kTopBarH))};
    ctx.draw().rect(bar, ctx.theme().panel);
    ctx.draw().rect({0, bar.bottom() - 1, bar.w, 1}, ctx.theme().panel_border);
    block(s, bar);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float pad = ctx.s(12.0f);
    float x = pad;

    // Goods: food as one total (with the kinds in the tooltip), then
    // everything else the town has.
    const std::vector<std::int32_t> stored = game.stored(s.town());
    std::int32_t food = 0;
    std::string food_detail;
    for (std::size_t r = 0; r < stored.size(); ++r) {
        if (content.resources[r].category == sim::ResourceCategory::Food) {
            food += stored[r];
            if (stored[r] > 0) {
                food_detail += (food_detail.empty() ? "" : "\n") + tr("hud.amount", tr(content.resources[r].name_key), stored[r]);
            }
        }
    }
    const auto item = [&](const std::string& text, const std::string& tooltip, const char* id) {
        const float w = ctx.text().measure(st, text) + ctx.s(18.0f);
        const ui::Rect r{x, bar.y, w, bar.h};
        ctx.label(r, text, st, ctx.theme().text);
        ctx.tooltip_area(ctx.id(id), r, tooltip);
        x += w;
    };
    item(tr("hud.food", food), food_detail.empty() ? tr("hud.food.tooltip") : food_detail, "hud_food");
    for (std::size_t r = 0; r < stored.size(); ++r) {
        const sim::ResourceDef& def = content.resources[r];
        if (def.category == sim::ResourceCategory::Food || (stored[r] == 0 && def.id != "core:log" && def.id != "core:stone")) {
            continue;
        }
        item(tr("hud.amount", tr(def.name_key), stored[r]), tr(def.name_key), def.id.c_str());
    }

    // Population and date in the middle-right; speed on the right.
    const std::int32_t pop = game.population(s.town());
    const std::int32_t adults = game.population(s.town(), true);
    const sim::Calendar cal = game.calendar();
    const float button = std::round(ctx.s(36.0f));
    const float gap = ctx.s(4.0f);
    float right = bar.right() - pad - 4 * button - 3 * gap;
    struct Speed {
        int value;
        const char* label;
        const char* tooltip;
    };
    static constexpr Speed kSpeeds[] = {{0, "hud.speed.pause", "hud.speed.pause.tooltip"},
                                        {1, "hud.speed.1", "hud.speed.1.tooltip"},
                                        {2, "hud.speed.2", "hud.speed.2.tooltip"},
                                        {3, "hud.speed.3", "hud.speed.3.tooltip"}};
    for (std::size_t i = 0; i < std::size(kSpeeds); ++i) {
        const ui::Rect r{right + static_cast<float>(i) * (button + gap), std::round((bar.h - button) * 0.5f), button, button};
        if (ctx.button(ctx.id(kSpeeds[i].label), r, tr(kSpeeds[i].label), tr(kSpeeds[i].tooltip), true,
                       services_.game_speed() == kSpeeds[i].value)) {
            services_.set_game_speed(kSpeeds[i].value);
        }
    }
    network(ctx, s, right);
    // Season and weather, then the date.
    static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                  "hud.season.winter"};
    const std::string weather = tr("hud.weather", tr(kSeasonKeys[static_cast<std::size_t>(cal.season) % 4]),
                                   game.temperature());
    const float ww = ctx.text().measure(st, weather) + ctx.s(24.0f);
    right -= ww;
    ctx.label({right, bar.y, ww, bar.h}, weather, st, game.temperature() < 0 ? ui::Color::rgb(0x9CC7F0) : ctx.theme().text);
    ctx.tooltip_area(ctx.id("hud_weather"), {right, bar.y, ww, bar.h},
                     tr(game.frozen() ? "hud.weather.frozen" : "hud.weather.tooltip", game.snow()));
    const std::string date_text = tr("hud.date", static_cast<int>(cal.year), static_cast<int>(cal.month),
                                     static_cast<int>(cal.day));
    const float dw = ctx.text().measure(st, date_text) + ctx.s(24.0f);
    right -= dw;
    ctx.label({right, bar.y, dw, bar.h}, date_text, st, ctx.theme().text_dim);
    const std::string pop_text = tr("hud.population", pop, adults);
    const float pw = ctx.text().measure(st, pop_text) + ctx.s(24.0f);
    right -= pw;
    ctx.label({right, bar.y, pw, bar.h}, pop_text, st, ctx.theme().text);
    const sim::PlayerState& ps = game.player(s.town());
    ctx.tooltip_area(ctx.id("hud_population"), {right, bar.y, pw, bar.h},
                     tr("hud.population.tooltip", ps.births, ps.arrivals, ps.deaths));
}

void GameHud::network(ui::Context& ctx, GameSession& s, float& right) {
    net::NetSession* net = services_.net();
    if (net == nullptr || !s.networked()) {
        return;
    }
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float bar_h = std::round(ctx.s(kTopBarH));
    // Players: a count, with the names in the tooltip.
    int connected = 0;
    std::string names;
    std::string waiting;
    for (const net::LobbyPlayer& p : net->lobby().players) {
        connected += p.connected ? 1 : 0;
        names += (names.empty() ? "" : "\n") + tr(p.connected ? "hud.net.player" : "hud.net.playerAway", p.name);
        if (net->waiting_for() && *net->waiting_for() == p.slot && p.slot != net->local_slot()) {
            waiting = p.name;
        }
    }
    const std::string text = tr("hud.net.players", connected);
    const float w = ctx.text().measure(st, text) + ctx.s(24.0f);
    right -= w;
    ctx.label({right, 0, w, bar_h}, text, st, ctx.theme().text);
    ctx.tooltip_area(ctx.id("hud_players"), {right, 0, w, bar_h}, names);

    // Waiting for somebody.
    if (!waiting.empty()) {
        const std::string wt = tr("hud.net.waiting", waiting);
        const float ww = ctx.text().measure(st, wt) + ctx.s(32.0f);
        const ui::Rect r{std::round((ctx.width() - ww) * 0.5f), bar_h + ctx.s(10.0f), std::round(ww),
                         std::round(ctx.text().line_height(st) + ctx.s(12.0f))};
        ctx.draw().rect(r, ctx.theme().tooltip.with_alpha(0.85f));
        ctx.label(r, wt, st, ctx.theme().text, ui::Align::Center);
    }

    // A speed vote someone else asked for.
    const std::optional<net::SpeedVote>& vote = net->vote();
    if (vote && vote->from != net->local_slot() && answered_vote_ != vote->id) {
        std::string from;
        for (const net::LobbyPlayer& p : net->lobby().players) {
            from = p.slot == vote->from ? p.name : from;
        }
        const std::string q = tr("hud.net.vote", from, static_cast<int>(vote->speed));
        const float pad = ctx.s(12.0f);
        const float bh = std::round(ctx.s(36.0f));
        const float vw = std::min(ctx.width() - 2 * pad, std::max(ctx.s(360.0f), ctx.text().measure(st, q) + 2 * pad));
        const float vh = ctx.text().line_height(st) + bh + 3 * pad;
        const ui::Rect box{std::round((ctx.width() - vw) * 0.5f), std::round(bar_h + ctx.s(56.0f)), std::round(vw),
                           std::round(vh)};
        ctx.panel(box);
        block(s, box);
        ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, ctx.text().line_height(st)}, q, st, ctx.theme().text);
        const float bw = (box.w - 3 * pad) * 0.5f;
        const float by = box.bottom() - pad - bh;
        if (ctx.button(ctx.id("vote_yes"), {box.x + pad, by, bw, bh}, tr("hud.net.accept"), {}, true, true)) {
            net->answer_vote(true);
            answered_vote_ = vote->id;
        } else if (ctx.button(ctx.id("vote_no"), {box.x + 2 * pad + bw, by, bw, bh}, tr("hud.net.refuse"))) {
            net->answer_vote(false);
            answered_vote_ = vote->id;
        }
    }
}

void GameHud::build_bar(ui::Context& ctx, GameSession& s) {
    const sim::Content& content = s.game().content();
    GameSession::Interaction& ui = s.ui();
    std::vector<sim::DefIndex> defs;
    for (std::size_t i = 0; i < content.buildings.size(); ++i) {
        if (content.buildings[i].kind != sim::BuildingKind::TownCenter) {
            defs.push_back(static_cast<sim::DefIndex>(i));
        }
    }
    if (defs.empty()) {
        return;
    }
    const float bw = std::round(ctx.s(kBuildButtonW));
    const float bh = std::round(ctx.s(kBuildButtonH));
    const float gap = ctx.s(6.0f);
    const float pad = ctx.s(8.0f);
    // As many per row as fit.
    const auto per_row = static_cast<std::size_t>(std::max(1.0f, (ctx.width() - 2 * pad + gap) / (bw + gap)));
    const std::size_t rows = (defs.size() + per_row - 1) / per_row;
    const std::size_t cols = std::min(per_row, defs.size());
    const float w = static_cast<float>(cols) * (bw + gap) - gap + 2 * pad;
    const float h = static_cast<float>(rows) * (bh + gap) - gap + 2 * pad;
    const ui::Rect panel{std::round((ctx.width() - w) * 0.5f), std::round(ctx.height() - h), std::round(w), std::round(h)};
    ctx.panel(panel);
    block(s, panel);
    ctx.push_id("build_bar");
    for (std::size_t i = 0; i < defs.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[defs[i]];
        const float bx = panel.x + pad + static_cast<float>(i % per_row) * (bw + gap);
        const float by = panel.y + pad + static_cast<float>(i / per_row) * (bh + gap);
        std::string tooltip = tr(d.name_key) + "\n" + tr("hud.build.cost", cost_text(d)) + "\n" +
                              tr("hud.build.size", d.width, d.depth);
        if (d.workers > 0) {
            tooltip += "\n" + tr("hud.build.workers", d.workers);
        }
        if (d.residents > 0) {
            tooltip += "\n" + tr("hud.build.residents", d.residents);
        }
        if (d.storage > 0) {
            tooltip += "\n" + tr("hud.build.storage", d.storage);
        }
        if (ctx.button(ctx.id(d.id), {bx, by, bw, bh}, tr(d.name_key), tooltip, true, ui.placing == defs[i])) {
            ui.placing = ui.placing == defs[i] ? sim::kNoDef : defs[i];
            ui.selected_building = {};
            ui.selected_villager = {};
        }
    }
    ctx.pop_id();
}

void GameHud::placement_hint(ui::Context& ctx, GameSession& s) {
    const GameSession::Interaction& ui = s.ui();
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const KeyBindings& b = services_.settings().input.bindings;
    std::string text = ui.field_farm.valid() ? tr("hud.place.field.hint")
                                             : tr("hud.place.hint", key_display_name(b.key(Action::GameRotateBuilding, 0)));
    ui::Color color = ctx.theme().text;
    if (ui.hover_valid && ui.hover_error != sim::PlaceError::None) {
        text = tr(place_error_key(ui.hover_error));
        color = ctx.theme().danger;
    }
    const float w = std::min(ctx.width() - ctx.s(32.0f), ctx.text().measure(st, text) + ctx.s(32.0f));
    const float h = ctx.text().line_height(st) + ctx.s(14.0f);
    const float y = ctx.height() - ctx.s(kBuildButtonH) * 2.0f - ctx.s(60.0f) - h;
    const ui::Rect r{std::round((ctx.width() - w) * 0.5f), std::round(y), std::round(w), std::round(h)};
    ctx.draw().rect(r, ctx.theme().tooltip.with_alpha(0.85f));
    ctx.label(r, text, st, color, ui::Align::Center);
}

void GameHud::building_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    GameSession::Interaction& ui = s.ui();
    const sim::Building* b = game.buildings().get(ui.selected_building);
    if (b == nullptr) {
        return;
    }
    const sim::BuildingDef& d = content.buildings[b->def];
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);

    // Lines first, to size the window.
    std::vector<std::string> lines;
    float progress = -1.0f;
    if (b->state == sim::BuildingState::Construction) {
        progress = d.build_work > 0 ? static_cast<float>(b->work_done) / static_cast<float>(d.build_work) : 1.0f;
        lines.push_back(tr("hud.building.construction", static_cast<int>(std::lround(progress * 100.0f))));
        for (const sim::ResourceAmount& c : d.cost) {
            std::int32_t have = 0;
            for (const sim::Stock& st : b->delivered) {
                have += st.resource == c.resource ? st.amount : 0;
            }
            lines.push_back(tr("hud.building.material", tr(content.resources[c.resource].name_key), have, c.amount));
        }
    } else {
        if (d.residents > 0) {
            lines.push_back(tr("hud.building.residents", static_cast<int>(b->residents.size()), d.residents));
            if (d.kind == sim::BuildingKind::House) {
                const sim::DefIndex fw = content.find_resource("core:firewood");
                std::int32_t wood = 0;
                for (const sim::Stock& st : b->stock) {
                    wood += st.resource == fw ? st.amount : 0;
                }
                lines.push_back(tr("hud.building.firewood", wood, sim::village::kHouseFirewood));
                if (!b->heated) {
                    lines.push_back(tr("hud.building.cold"));
                }
            }
        }
        if (d.storage > 0) {
            std::int32_t total = 0;
            for (const sim::Stock& st : b->stock) {
                total += st.amount;
            }
            lines.push_back(tr("hud.building.storage", total, d.storage));
            for (const sim::Stock& st : b->stock) {
                if (st.amount > 0 && lines.size() < 16) {
                    lines.push_back("  " + tr("hud.amount", tr(content.resources[st.resource].name_key), st.amount));
                }
            }
        }
    }
    const bool has_workers = d.workers > 0 && b->state == sim::BuildingState::Complete;
    const bool farm = d.work == sim::WorkKind::Farm && b->state == sim::BuildingState::Complete;
    const float field_row = std::round(ctx.s(30.0f));
    const float button_h = std::round(ctx.s(34.0f));
    const float title_h = ctx.text().line_height(title);
    float h = pad + title_h + pad * 0.5f + static_cast<float>(lines.size()) * line;
    if (progress >= 0.0f) {
        h += ctx.s(14.0f);
    }
    if (has_workers) {
        h += button_h + pad * 0.5f;
    }
    const bool removable = ui.selected_building != game.player(s.town()).town_center;
    if (removable) {
        h += button_h + pad * 0.5f;
    }
    if (farm) {
        h += static_cast<float>(b->fields.size()) * (line + field_row + pad * 0.5f) + button_h + pad;
    }
    h += pad;
    const ui::Rect box{std::round(ctx.width() - w - pad), std::round(ctx.s(kTopBarH) + pad), std::round(w), std::round(h)};
    ctx.panel(box);
    block(s, box);
    ctx.push_id("building_window");
    float y = box.y + pad;
    ctx.label({box.x + pad, y, box.w - 2 * pad - button_h, title_h}, tr(d.name_key), title, ctx.theme().accent);
    if (ctx.button(ctx.id("close"), {box.right() - pad - button_h, y, button_h, button_h}, tr("hud.close"),
                   tr("hud.close.tooltip"))) {
        ui.selected_building = {};
    }
    y += title_h + pad * 0.5f;
    if (progress >= 0.0f) {
        meter(ctx, {box.x + pad, y, box.w - 2 * pad, ctx.s(8.0f)}, progress, ctx.theme().accent);
        y += ctx.s(14.0f);
    }
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
    if (has_workers) {
        y += pad * 0.5f;
        const std::string text = tr("hud.building.workers", static_cast<int>(b->workers.size()), b->wanted_workers, d.workers);
        ctx.label({box.x + pad, y, box.w - 2 * pad - 2 * button_h - ctx.s(8.0f), button_h}, text, body, ctx.theme().text);
        const auto set_workers = [&](std::int32_t n) {
            sim::Command c;
            c.type = sim::CommandType::SetWorkers;
            c.entity = ui.selected_building;
            c.value = n;
            s.issue(c);
        };
        const ui::Rect minus{box.right() - pad - 2 * button_h - ctx.s(4.0f), y, button_h, button_h};
        const ui::Rect plus{box.right() - pad - button_h, y, button_h, button_h};
        if (ctx.button(ctx.id("fewer"), minus, tr("hud.building.fewer"), tr("hud.building.fewer.tooltip"),
                       b->wanted_workers > 0)) {
            set_workers(b->wanted_workers - 1);
        }
        if (ctx.button(ctx.id("more"), plus, tr("hud.building.more"), tr("hud.building.more.tooltip"),
                       b->wanted_workers < d.workers)) {
            set_workers(b->wanted_workers + 1);
        }
        y += button_h;
    }
    if (farm) {
        y += pad * 0.5f;
        farm_fields(ctx, s, *b, box, y, field_row);
    }
    if (removable) {
        y += pad * 0.5f;
        const bool building = b->state == sim::BuildingState::Construction;
        if (ctx.button(ctx.id("remove"), {box.x + pad, y, box.w - 2 * pad, button_h},
                       tr(building ? "hud.building.cancel" : "hud.building.demolish"),
                       tr(building ? "hud.building.cancel.tooltip" : "hud.building.demolish.tooltip"))) {
            sim::Command c;
            c.type = sim::CommandType::RemoveBuilding;
            c.entity = ui.selected_building;
            s.issue(c);
            ui.selected_building = {};
        }
    }
    ctx.pop_id();
}

void GameHud::farm_fields(ui::Context& ctx, GameSession& s, const sim::Building& b, const ui::Rect& box, float& y,
                          float row_h) {
    const sim::Content& content = s.game().content();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float gap = ctx.s(4.0f);
    GameSession::Interaction& ui = s.ui();
    static constexpr const char* kStateKeys[] = {"hud.farm.waiting", "hud.farm.growing", "hud.farm.ripe", "hud.farm.done"};
    const auto crop_name = [&](sim::DefIndex c) {
        return c < content.crops.size() ? tr(content.crops[c].name_key) : tr("hud.farm.fallow");
    };
    for (std::size_t i = 0; i < b.fields.size(); ++i) {
        const sim::Field& f = b.fields[i];
        std::string state = tr(kStateKeys[static_cast<std::size_t>(f.state) % 4]);
        if (f.state == sim::FieldState::Growing) {
            state = tr("hud.farm.growingPercent", f.growth / 10);
        } else if (f.state == sim::FieldState::Done && f.plan[f.slot] == sim::kNoDef) {
            state = tr("hud.farm.resting");
        }
        ctx.label({box.x + pad, y, box.w - 2 * pad, line},
                  tr("hud.farm.field", static_cast<int>(i + 1), f.w, f.d, f.fertility, state), small, ctx.theme().text);
        y += line;
        // The three years of the plan; this year's is highlighted. A click
        // moves to the next crop (fallow last).
        const float slot_w = (box.w - 2 * pad - row_h - 3 * gap) / 3.0f;
        ctx.push_id("field" + std::to_string(i));
        for (std::size_t year = 0; year < sim::kPlanYears; ++year) {
            const ui::Rect r{box.x + pad + static_cast<float>(year) * (slot_w + gap), y, slot_w, row_h};
            if (ctx.button(ctx.id("year" + std::to_string(year)), r, crop_name(f.plan[year]), tr("hud.farm.plan.tooltip"),
                           true, year == f.slot)) {
                sim::DefIndex next = sim::kNoDef;
                if (f.plan[year] == sim::kNoDef) {
                    next = content.crops.empty() ? sim::kNoDef : 0;
                } else if (f.plan[year] + 1u < content.crops.size()) {
                    next = static_cast<sim::DefIndex>(f.plan[year] + 1);
                }
                sim::Command c;
                c.type = sim::CommandType::SetCrop;
                c.entity = ui.selected_building;
                c.def = next;
                c.value = static_cast<std::int32_t>(i) | static_cast<std::int32_t>(year << 8);
                s.issue(c);
            }
        }
        if (ctx.button(ctx.id("remove"), {box.right() - pad - row_h, y, row_h, row_h}, tr("hud.close"),
                       tr("hud.farm.remove.tooltip"))) {
            sim::Command c;
            c.type = sim::CommandType::RemoveField;
            c.entity = ui.selected_building;
            c.value = static_cast<std::int32_t>(i);
            s.issue(c);
        }
        ctx.pop_id();
        y += row_h + pad * 0.5f;
    }
    const bool room = static_cast<std::int32_t>(b.fields.size()) < content.buildings[b.def].fields;
    const float button_h = std::round(ctx.s(34.0f));
    if (ctx.button(ctx.id("new_field"), {box.x + pad, y, box.w - 2 * pad, button_h}, tr("hud.farm.newField"),
                   tr(room ? "hud.farm.newField.tooltip" : "hud.farm.full"), room, ui.field_farm == ui.selected_building)) {
        ui.field_farm = ui.selected_building;
        ui.placing = sim::kNoDef;
    }
    y += button_h;
}

void GameHud::villager_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    GameSession::Interaction& ui = s.ui();
    const sim::Villager* v = game.villagers().get(ui.selected_villager);
    if (v == nullptr) {
        return;
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    const std::int32_t age = game.age_years(*v);

    std::vector<std::string> lines;
    lines.push_back(tr("hud.villager.age", age));
    lines.push_back(tr("hud.villager.task", tr(task_text_key(v->task))));
    const sim::Building* job = game.buildings().get(v->job);
    lines.push_back(job != nullptr ? tr("hud.villager.job", tr(content.buildings[job->def].name_key))
                                   : tr(game.adult(*v) ? "hud.villager.laborer" : "hud.villager.child"));
    lines.push_back(tr(game.buildings().get(v->home) != nullptr ? "hud.villager.housed" : "hud.villager.homeless"));
    lines.push_back(tr(v->clothes > 0 ? "hud.villager.clothes" : "hud.villager.noClothes"));
    if (v->carrying.amount > 0 && v->carrying.resource < content.resources.size()) {
        lines.push_back(tr("hud.villager.carrying", tr("hud.amount", tr(content.resources[v->carrying.resource].name_key),
                                                       v->carrying.amount)));
    }
    const float bar_block = 3 * (line + ctx.s(10.0f));
    const float title_h = ctx.text().line_height(title);
    const float button_h = std::round(ctx.s(34.0f));
    const float h = pad + title_h + pad * 0.5f + static_cast<float>(lines.size()) * line + bar_block + pad;
    const ui::Rect box{std::round(ctx.width() - w - pad), std::round(ctx.s(kTopBarH) + pad), std::round(w), std::round(h)};
    ctx.panel(box);
    block(s, box);
    ctx.push_id("villager_window");
    float y = box.y + pad;
    const bool female = v->sex == sim::Sex::Female;
    const char* name_key = !game.adult(*v) ? (female ? "hud.villager.girl" : "hud.villager.boy")
                                           : (female ? "hud.villager.woman" : "hud.villager.man");
    ctx.label({box.x + pad, y, box.w - 2 * pad - button_h, title_h}, tr(name_key), title, ctx.theme().accent);
    if (ctx.button(ctx.id("close"), {box.right() - pad - button_h, y, button_h, button_h}, tr("hud.close"),
                   tr("hud.close.tooltip"))) {
        ui.selected_villager = {};
    }
    y += title_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
    const auto bar = [&](const std::string& label, float fraction, ui::Color color) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, label, body, ctx.theme().text_dim);
        y += line;
        meter(ctx, {box.x + pad, y, box.w - 2 * pad, ctx.s(8.0f)}, fraction, color);
        y += ctx.s(10.0f);
    };
    bar(tr("hud.villager.food"), static_cast<float>(v->food) / static_cast<float>(sim::village::kFoodMax),
        v->food < sim::village::kEatBelow / 2 ? ctx.theme().danger : ctx.theme().accent);
    bar(tr("hud.villager.warmth"), static_cast<float>(v->warmth) / static_cast<float>(sim::village::kWarmthMax),
        v->warmth < sim::village::kWarmthMax / 3 ? ctx.theme().danger : ui::Color::rgb(0xE08A3C));
    bar(tr("hud.villager.health"), static_cast<float>(v->health) / static_cast<float>(sim::village::kHealthMax),
        v->health < sim::village::kHealthMax / 2 ? ctx.theme().danger : ui::Color::rgb(0x6FAF5A));
    ctx.pop_id();
}

}  // namespace sc
