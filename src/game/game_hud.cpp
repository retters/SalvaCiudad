#include "game/game_hud.h"

#include "core/speed.h"

#include <algorithm>
#include <functional>
#include <cmath>

#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 44.0f;
constexpr float kBuildButtonW = 150.0f;
constexpr float kBuildButtonH = 44.0f;
constexpr float kWindowW = 400.0f;  // Room for the title beside its three buttons.

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
        case sim::PlaceError::Locked: return "hud.place.error.locked";
        case sim::PlaceError::Unexplored: return "hud.place.error.unexplored";
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

const char* need_text_key(std::uint8_t need) {
    static constexpr const char* kKeys[] = {"need.food",   "need.water",   "need.clothes", "need.shoes",
                                            "need.religion", "need.entertainment", "need.heating", "need.beauty",
                                            "need.market", "need.hygiene", "need.healer", "need.doctor"};
    return need < std::size(kKeys) ? kKeys[need] : "need.food";
}

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
        case sim::Task::GoFire: return "task.goFire";
        case sim::Task::FightFire: return "task.fightFire";
        case sim::Task::GoFight: return "task.goFight";
        case sim::Task::Fight: return "task.fight";
        case sim::Task::Flee: return "task.flee";
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

std::string speed_text(int quarters) {
    if (quarters == 1) {
        return tr("speed.quarter");
    }
    if (quarters == 2) {
        return tr("speed.half");
    }
    return std::to_string(quarters / speed::kNormal);
}

namespace {

float meters(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

// Whether a natural feature is still there to look at: not felled or dug
// out (a picked bush that grows back is).
bool node_there(const sim::Game& game, std::uint32_t index) {
    return index < game.nodes().size() && index < game.map().features.size() &&
           (game.nodes()[index].amount > 0 || game.nodes()[index].regrow_tick != 0);
}

// The thing selected on the map, as the windows name it.
struct Selected {
    bool valid = false;
    WindowList::Kind kind = WindowList::Kind::Building;
    sim::EntityId entity;
};
Selected selected(const GameSession::Interaction& ui) {
    if (ui.selected_building.valid()) {
        return {true, WindowList::Kind::Building, ui.selected_building};
    }
    if (ui.selected_villager.valid()) {
        return {true, WindowList::Kind::Villager, ui.selected_villager};
    }
    if (ui.selected_creature.valid()) {
        return {true, WindowList::Kind::Creature, ui.selected_creature};
    }
    if (ui.selected_node != 0) {
        return {true, WindowList::Kind::Node, sim::EntityId{ui.selected_node - 1, 0}};
    }
    return {};
}

const char* feature_key(sim::FeatureType type) {
    switch (type) {
        case sim::FeatureType::Stone: return "feature.stone";
        case sim::FeatureType::IronOre: return "feature.ironOre";
        case sim::FeatureType::BerryBush: return "feature.berryBush";
        case sim::FeatureType::Herbs: return "feature.herbs";
        default: return "feature.tree";
    }
}

const char* creature_key(sim::CreatureKind kind) {
    switch (kind) {
        case sim::CreatureKind::Deer: return "hud.creature.deer";
        case sim::CreatureKind::Boar: return "hud.creature.boar";
        case sim::CreatureKind::Wolf: return "hud.creature.wolf";
        case sim::CreatureKind::Bear: return "hud.creature.bear";
        case sim::CreatureKind::Raider: return "hud.creature.raider";
        default: return "hud.creature.soldier";
    }
}

const char* creature_state_key(sim::CreatureState state) {
    switch (state) {
        case sim::CreatureState::Flee: return "hud.creature.state.flee";
        case sim::CreatureState::Chase: return "hud.creature.state.chase";
        case sim::CreatureState::Approach: return "hud.creature.state.approach";
        case sim::CreatureState::Bash: return "hud.creature.state.bash";
        case sim::CreatureState::Leave: return "hud.creature.state.leave";
        case sim::CreatureState::Travel: return "hud.creature.state.travel";
        default: return "hud.creature.state.wander";
    }
}

constexpr std::size_t kPeopleRows = 5;  // More than these scroll.

}  // namespace

bool GameHud::pressed(const ui::Context& ctx, Action action) const {
    const KeyBindings& b = services_.settings().input.bindings;
    for (const SDL_Scancode k : ctx.input().keys) {
        if (b.matches(action, k)) {
            return true;
        }
    }
    return false;
}

void GameHud::mark(ui::Context& ctx, const ui::Rect& r) const {
    // A gold outline that pulses about once a second.
    const double t = static_cast<double>(ctx.now_ns() % 1'000'000'000ull) / 1e9;
    const auto alpha = static_cast<std::uint8_t>(140 + 115 * std::abs(std::sin(t * 3.14159)));
    const float th = std::max(2.0f, std::round(ctx.s(3.0f)));
    const ui::Rect o{r.x - th, r.y - th, r.w + 2 * th, r.h + 2 * th};
    ctx.draw().rect_outline(o, ctx.theme().accent.with_alpha(alpha / 255.0f), th);
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
    if (ui.selected_creature.valid() && game.creatures().get(ui.selected_creature) == nullptr) {
        ui.selected_creature = {};
    }
    if (ui.selected_node != 0 && !node_there(game, ui.selected_node - 1)) {
        ui.selected_node = 0;
    }

    // Another game: the windows of the last one's things go.
    if (windows_session_ != s) {
        windows_session_ = s;
        windows_.clear_objects();
        selected_shown_ = {};
    }
    windows_begin(ctx);

    bool open_menu = false;
    if (!blocked) {
        if (pressed(ctx, Action::GameRotateBuilding) && ui.placing != sim::kNoDef) {
            ui.rotation = static_cast<std::uint8_t>((ui.rotation + 1) & 3u);
        }
        if (ctx.input().key(SDL_SCANCODE_ESCAPE) && ctx.typing()) {
            rename_id_.clear();  // Esc while typing a name: only the typing ends.
        } else if (ctx.input().key(SDL_SCANCODE_ESCAPE)) {
            if (ui.field_farm.valid()) {
                ui.field_farm = {};
                ui.field_dragging = false;
            } else if (ui.placing != sim::kNoDef) {
                ui.placing = sim::kNoDef;
            } else if (ui.any_selected() || windows_.passing() != nullptr) {
                // Only the passing window goes; the pinned ones stay.
                ui.clear_selection();
                windows_.close_passing();
            } else {
                open_menu = true;
            }
        }
    }
    sync_selection(ctx, *s);

    // Under a window, the rest of the interface does not hear the mouse.
    const bool covered = !hover_top_.empty();
    ctx.set_input_blocked(blocked || covered);
    top_bar(ctx, *s);
    build_bar(ctx, *s);
    minimap(ctx, *s, blocked);  // It knows by itself what lies over it.
    if (ui.placing != sim::kNoDef || ui.field_farm.valid()) {
        placement_hint(ctx, *s);
    }
    dock(ctx, *s);
    notifications(ctx, *s, build_bar_top_);

    // The windows, from the back to the front; only the one in front under
    // the cursor (or the one being dragged) hears the mouse.
    struct Job {
        std::string id;
        std::function<void()> draw;
    };
    std::vector<Job> jobs;
    const auto fixed = [&](const char* id, bool& open, void (GameHud::*draw)(ui::Context&, GameSession&)) {
        if (open) {
            jobs.push_back({id, [this, &ctx, s, draw] { (this->*draw)(ctx, *s); }});
        } else if (windows_.open(id)) {
            windows_.close(id);
        }
    };
    fixed("trade", trade_open_, &GameHud::trade_window);
    fixed("army", army_open_, &GameHud::army_window);
    fixed("goods", goods_open_, &GameHud::goods_window);
    fixed("stats", stats_open_, &GameHud::stats_window);
    fixed("log", log_open_, &GameHud::log_window);
    fixed("layers", layers_open_, &GameHud::layers_window);
    for (const WindowList::Object& o : windows_.objects()) {
        jobs.push_back({o.id, [this, &ctx, s, o] {
                            switch (o.kind) {
                                case WindowList::Kind::Building: building_window(ctx, *s, o); break;
                                case WindowList::Kind::Villager: villager_window(ctx, *s, o); break;
                                case WindowList::Kind::Node: node_window(ctx, *s, o); break;
                                case WindowList::Kind::Creature: creature_window(ctx, *s, o); break;
                            }
                        }});
    }
    for (const Job& j : jobs) {
        if (!windows_.open(j.id)) {
            windows_.raise(j.id);  // Opened without a click (a trade offer): in front.
        }
    }
    const std::vector<std::string> order = windows_.order();
    for (const std::string& id : order) {
        const auto job = std::find_if(jobs.begin(), jobs.end(), [&](const Job& j) { return j.id == id; });
        // A window may have gone while the ones behind it were drawn.
        if (job == jobs.end() || (WindowList::is_object_id(id) && windows_.object(id) == nullptr)) {
            continue;
        }
        const bool mine = hover_top_.empty() || hover_top_ == id;
        ctx.set_input_blocked(blocked || !mine);
        ctx.push_id(id);
        job->draw();
        ctx.pop_id();
    }
    ctx.set_input_blocked(blocked);
    for (const std::string& id : closing_) {
        if (const WindowList::Object* o = windows_.object(id)) {
            // The selection goes with its window.
            const Selected sel = selected(ui);
            if (sel.valid && sel.kind == o->kind && sel.entity == o->entity) {
                ui.clear_selection();
            }
        }
        if (rename_id_ == id) {
            rename_id_.clear();
        }
        windows_.close(id);
    }
    closing_.clear();
    // Links pressed this frame: the window they are in stays, and the
    // thing becomes the selection (its window opens with the next frame).
    for (const Link& link : links_) {
        if (windows_.object(link.from) != nullptr) {
            windows_.place(link.from).pinned = true;
        }
        ui.clear_selection();
        switch (link.kind) {
            case WindowList::Kind::Building: ui.selected_building = link.entity; break;
            case WindowList::Kind::Villager: ui.selected_villager = link.entity; break;
            case WindowList::Kind::Node: ui.selected_node = link.entity.index + 1; break;
            case WindowList::Kind::Creature: ui.selected_creature = link.entity; break;
        }
    }
    links_.clear();
    windows_end(ctx);
    return open_menu;
}

void GameHud::sync_selection(ui::Context& ctx, GameSession& s) {
    GameSession::Interaction& ui = s.ui();
    const sim::Game& game = s.game();
    const Selected sel = selected(ui);
    const sim::EntityId now = sel.valid ? sel.entity : sim::EntityId{};
    const WindowList::Kind kind = sel.kind;
    if (now != selected_shown_ || (sel.valid && kind != selected_kind_)) {
        if (sel.valid) {
            if (windows_.select(kind, now).empty()) {
                notify(tr("hud.window.limit", static_cast<int>(WindowList::kMaxObjects)), false, 0.0f, 0.0f,
                       game.calendar(), ctx.now_ns());
            }
        } else {
            windows_.close_passing();  // A click on the ground, the build bar...
        }
        selected_shown_ = now;
        selected_kind_ = kind;
    }
    // The passing window of a thing that is no more goes; a pinned one
    // stays to say so.
    if (const WindowList::Object* o = windows_.passing()) {
        bool there = false;
        switch (o->kind) {
            case WindowList::Kind::Building: there = game.buildings().get(o->entity) != nullptr; break;
            case WindowList::Kind::Villager: there = game.villagers().get(o->entity) != nullptr; break;
            case WindowList::Kind::Node: there = node_there(game, o->entity.index); break;
            case WindowList::Kind::Creature: there = game.creatures().get(o->entity) != nullptr; break;
        }
        if (!there) {
            windows_.close_passing();
        }
    }
}

void GameHud::gone_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    const std::string text = tr(o.kind == WindowList::Kind::Building   ? "hud.window.gone.building"
                                : o.kind == WindowList::Kind::Villager ? "hud.window.gone.villager"
                                                                       : "hud.window.gone.thing");
    const float text_h = ctx.paragraph_height(w - 2 * pad, text, body);
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(pad + title_h + pad + text_h + pad)};
    bool open = true;
    if (!window(ctx, s, o.id, tr("hud.window.gone.title"), box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    (void)ctx.paragraph({box.x + pad, box.y + pad + title_h + pad, box.w - 2 * pad, text_h}, text, body, ctx.theme().text_dim);
}

void GameHud::top_bar(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const ui::Rect bar{0, 0, ctx.width(), std::round(ctx.s(kTopBarH))};
    top_bar_bottom_ = bar.bottom();
    ctx.draw().rect(bar, ctx.theme().panel);
    ctx.draw().rect({0, bar.bottom() - 1, bar.w, 1}, ctx.theme().panel_border);
    block(s, bar);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float pad = ctx.s(12.0f);
    float x = pad;

    // Population and date in the middle-right; speed on the right.
    const std::int32_t pop = game.population(s.town());
    const std::int32_t adults = game.population(s.town(), true);
    const sim::Calendar cal = game.calendar();
    const float button = std::round(ctx.s(36.0f));
    const float gap = ctx.s(4.0f);
    // Pause, and "- xN +" (phase 58).
    const float label_w = std::round(ctx.s(56.0f));
    float right = bar.right() - pad - 3 * button - label_w - 3 * gap;
    {
        const float by = std::round((bar.h - button) * 0.5f);
        const int now = services_.game_speed();
        const int most = services_.max_game_speed();
        float sx = right;
        if (ctx.button(ctx.id("hud.speed.pause"), {sx, by, button, button}, tr("hud.speed.pause"), tr("hud.speed.pause.tooltip"),
                       true, now == speed::kPause)) {
            services_.set_game_speed(now == speed::kPause ? shown_speed_ : speed::kPause);
        }
        if (now != speed::kPause) {
            shown_speed_ = now;  // What "xN" says while paused, and where the pause goes back to.
        }
        sx += button + gap;
        if (ctx.button(ctx.id("hud.speed.slower"), {sx, by, button, button}, tr("hud.speed.slower"),
                       tr("hud.speed.slower.tooltip"), shown_speed_ > speed::kMin)) {
            services_.set_game_speed(speed::slower(shown_speed_));
        }
        sx += button + gap;
        ctx.label({sx, by, label_w, button}, tr("hud.speed.value", speed_text(shown_speed_)), st,
                  now == speed::kPause ? ctx.theme().text_dim : ctx.theme().text, ui::Align::Center);
        sx += label_w + gap;
        const ui::Rect faster{sx, by, button, button};
        if (highlight_ == "speed") {
            mark(ctx, faster);
        }
        if (ctx.button(ctx.id("hud.speed.faster"), faster, tr("hud.speed.faster"), tr("hud.speed.faster.tooltip"),
                       shown_speed_ < most)) {
            services_.set_game_speed(speed::faster(shown_speed_, most));
        }
    }
    network(ctx, s, right);
    // Season and weather, then the date.
    static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                  "hud.season.winter"};
    const std::string weather = tr("hud.weather", tr(kSeasonKeys[static_cast<std::size_t>(cal.season) % 4]),
                                   game.temperature());
    const std::string date_text = tr("hud.date", static_cast<int>(cal.year), static_cast<int>(cal.month),
                                     static_cast<int>(cal.day));
    // Weather over the date, in two small lines.
    const ui::TextStyle two = ctx.style(ctx.theme().small);
    const float half = std::round(bar.h * 0.5f);
    const float ww = std::max(ctx.text().measure(two, weather), ctx.text().measure(two, date_text)) + ctx.s(24.0f);
    right -= ww;
    ctx.label({right, bar.y + ctx.s(3.0f), ww, half - ctx.s(3.0f)}, weather, two,
              game.temperature() < 0 ? ui::Color::rgb(0x9CC7F0) : ctx.theme().text);
    ctx.label({right, bar.y + half, ww, half - ctx.s(3.0f)}, date_text, two, ctx.theme().text_dim);
    ctx.tooltip_area(ctx.id("hud_weather"), {right, bar.y, ww, bar.h},
                     tr(game.frozen() ? "hud.weather.frozen" : "hud.weather.tooltip", game.snow()));
    // Two small lines in one slot of the bar.
    const ui::TextStyle small2 = ctx.style(ctx.theme().small);
    const float half2 = std::round(bar.h * 0.5f);
    const auto stacked = [&](const std::string& top, ui::Color top_color, const std::string& bottom, ui::Color bottom_color,
                             const char* id, const std::string& tooltip) {
        const float w = std::max(ctx.text().measure(small2, top), ctx.text().measure(small2, bottom)) + ctx.s(20.0f);
        right -= w;
        ctx.label({right, bar.y + ctx.s(3.0f), w, half2 - ctx.s(3.0f)}, top, small2, top_color);
        ctx.label({right, bar.y + half2, w, half2 - ctx.s(3.0f)}, bottom, small2, bottom_color);
        ctx.tooltip_area(ctx.id(id), {right, bar.y, w, bar.h}, tooltip);
    };
    // Happiness over the town's gold, and where the gold is.
    const std::int32_t joy = game.happiness(s.town());
    const sim::Game::GoldPlaces places = game.gold_places(s.town());
    stacked(tr("hud.happiness", joy), joy < 35 ? ctx.theme().danger : ctx.theme().text,
            tr("hud.gold", game.gold(s.town())), ui::Color::rgb(0xE8C45A), "hud_happiness",
            tr("hud.happiness.tooltip") + "\n" + tr("hud.gold.tooltip", places.post, places.vaults, places.others));
    // Troubles: the sick over the fires, only when there are some.
    const std::int32_t sick = game.sick(s.town());
    std::int32_t fires = 0;
    for (const sim::Building& b : game.buildings().data()) {
        fires += b.fire > 0 && b.owner == s.town() ? 1 : 0;
    }
    const std::int32_t raiders = game.raiders_near(s.town());
    if (raiders > 0) {
        stacked(tr("hud.raiders", raiders), ctx.theme().danger,
                tr(game.player(s.town()).alarm ? "hud.alarm.on" : "hud.alarm.off"), ctx.theme().text_dim, "hud_raiders",
                tr("hud.raiders.tooltip"));
    }
    if (sick > 0 || fires > 0) {
        stacked(tr("hud.sick", sick), ctx.theme().text, tr("hud.fires", fires),
                fires > 0 ? ctx.theme().danger : ctx.theme().text_dim, "hud_troubles", tr("hud.troubles.tooltip"));
    }
    // Trade with other towns.
    bool others = false;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        others = others || (game.town_of(p) == p && p != s.town() && game.player(p).active);
    }
    const std::string pop_text = tr("hud.population", pop);
    const float pw = ctx.text().measure(st, pop_text) + ctx.s(24.0f);
    right -= pw;
    ctx.label({right, bar.y, pw, bar.h}, pop_text, st, ctx.theme().text);
    const sim::PlayerState& ps = game.player(s.town());
    ctx.tooltip_area(ctx.id("hud_population"), {right, bar.y, pw, bar.h},
                     tr("hud.population.tooltip", adults, ps.births, ps.arrivals, ps.deaths));

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
    // What does not fit before the right side goes into a "+N" item.
    const float more_w = ctx.text().measure(st, tr("hud.more", 99)) + ctx.s(18.0f);
    int hidden = 0;
    std::string hidden_detail;
    const auto item = [&](const std::string& text, const std::string& tooltip, const char* id) {
        const float w = ctx.text().measure(st, text) + ctx.s(18.0f);
        if (hidden > 0 || x + w + more_w > right) {
            ++hidden;
            hidden_detail += (hidden_detail.empty() ? "" : "\n") + text;
            return;
        }
        const ui::Rect r{x, bar.y, w, bar.h};
        ctx.label(r, text, st, ctx.theme().text);
        ctx.tooltip_area(ctx.id(id), r, tooltip);
        x += w;
    };
    item(tr("hud.food", food), food_detail.empty() ? tr("hud.food.tooltip") : food_detail, "hud_food");
    for (std::size_t r = 0; r < stored.size(); ++r) {
        const sim::ResourceDef& def = content.resources[r];
        if (def.category == sim::ResourceCategory::Food || def.category == sim::ResourceCategory::Gold ||
            (stored[r] == 0 && def.id != "core:log" && def.id != "core:stone")) {
            continue;
        }
        item(tr("hud.amount", tr(def.name_key), stored[r]), tr(def.name_key), def.id.c_str());
    }
    if (hidden > 0) {
        const ui::Rect r{x, bar.y, more_w, bar.h};
        ctx.label(r, tr("hud.more", hidden), st, ctx.theme().text_dim);
        ctx.tooltip_area(ctx.id("hud_more"), r, hidden_detail);
    }
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
        const std::string q = tr("hud.net.vote", from, speed_text(vote->speed));
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
    static constexpr const char* kCategoryKeys[] = {"hud.build.cat.housing",  "hud.build.cat.food",
                                                    "hud.build.cat.resources", "hud.build.cat.industry",
                                                    "hud.build.cat.services", "hud.build.cat.decoration",
                                                    "hud.build.cat.defense"};
    constexpr std::size_t kCategories = std::size(kCategoryKeys);
    std::vector<sim::DefIndex> defs;
    for (std::size_t i = 0; i < content.buildings.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[i];
        if (d.kind != sim::BuildingKind::TownCenter && d.category % kCategories == category_ % kCategories) {
            defs.push_back(static_cast<sim::DefIndex>(i));
        }
    }
    const float bw = std::round(ctx.s(kBuildButtonW));
    const float bh = std::round(ctx.s(kBuildButtonH));
    const float tab_h = std::round(ctx.s(32.0f));
    const float gap = ctx.s(6.0f);
    const float pad = ctx.s(8.0f);
    // As many per row as fit; the tabs on top.
    const auto per_row = static_cast<std::size_t>(std::max(1.0f, (ctx.width() - 2 * pad + gap) / (bw + gap)));
    const std::size_t rows = std::max<std::size_t>(1, (defs.size() + per_row - 1) / per_row);
    const std::size_t cols = std::max(std::min(per_row, defs.size()), std::min(per_row, kCategories));
    const float w = static_cast<float>(cols) * (bw + gap) - gap + 2 * pad;
    const float h = tab_h + gap + static_cast<float>(rows) * (bh + gap) - gap + 2 * pad;
    const ui::Rect panel{std::round((ctx.width() - w) * 0.5f), std::round(ctx.height() - h), std::round(w), std::round(h)};
    ctx.panel(panel);
    block(s, panel);
    build_bar_top_ = panel.y;
    ctx.push_id("build_bar");
    const float tab_w = std::min(bw, (w - 2 * pad - gap * static_cast<float>(kCategories - 1)) / static_cast<float>(kCategories));
    // The tutorial may point at a building: its tab first, then its button.
    sim::DefIndex pointed = sim::kNoDef;
    if (highlight_.starts_with("build:")) {
        pointed = content.find_building(std::string_view(highlight_).substr(6));
    }
    for (std::size_t c = 0; c < kCategories; ++c) {
        const ui::Rect tr_rect{panel.x + pad + static_cast<float>(c) * (tab_w + gap), panel.y + pad, tab_w, tab_h};
        if (ctx.button(ctx.id(kCategoryKeys[c]), tr_rect, tr(kCategoryKeys[c]), {}, true, category_ == c)) {
            category_ = static_cast<std::uint8_t>(c);
        }
        if (pointed != sim::kNoDef && content.buildings[pointed].category % kCategories == c && category_ != c) {
            mark(ctx, tr_rect);
        }
    }
    const std::int32_t tier = s.game().tier(s.town());
    for (std::size_t i = 0; i < defs.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[defs[i]];
        const float bx = panel.x + pad + static_cast<float>(i % per_row) * (bw + gap);
        const float by = panel.y + pad + tab_h + gap + static_cast<float>(i / per_row) * (bh + gap);
        const bool locked = d.tier > tier;
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
        if (locked) {
            tooltip += "\n" + tr("hud.build.locked", d.tier);
        }
        if (d.service != sim::kNoNeed) {
            tooltip += "\n" + tr("hud.build.service", tr(need_text_key(d.service)), d.service_radius);
        }
        if (defs[i] == pointed) {
            mark(ctx, {bx, by, bw, bh});
        }
        if (ctx.button(ctx.id(d.id), {bx, by, bw, bh}, tr(d.name_key), tooltip, !locked, ui.placing == defs[i])) {
            ui.placing = ui.placing == defs[i] ? sim::kNoDef : defs[i];
            ui.clear_selection();
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

void GameHud::building_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    window_entity_ = o.entity;
    const sim::Building* b = game.buildings().get(o.entity);
    if (b == nullptr) {
        gone_window(ctx, s, o);
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
    if (b->damage > 0) {
        lines.push_back(tr("hud.building.damage", b->damage * 100 / std::max(1, d.hp)));
    }
    if (d.attack_range > 0 && b->state == sim::BuildingState::Complete) {
        lines.push_back(tr("hud.building.tower", d.attack_range, d.attack_damage));
    }
    if (d.trap && b->state == sim::BuildingState::Complete) {
        lines.push_back(tr(b->rearm > 0 ? "hud.building.trapRearming" : "hud.building.trapArmed"));
    }
    if (b->fire > 0) {
        lines.push_back(tr("hud.building.fire", b->fire, b->burned / 10));
    } else if (b->burned > 0) {
        lines.push_back(tr("hud.building.burned", b->burned / 10));
    }
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
                house_lines(game, *b, lines);
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
                if (st.amount > 0 && lines.size() < (d.trade ? 4u : 16u)) {
                    lines.push_back("  " + tr("hud.amount", tr(content.resources[st.resource].name_key), st.amount));
                }
            }
        }
    }
    const bool mine = b->owner == s.town();
    const bool has_workers = d.workers > 0 && b->state == sim::BuildingState::Complete;
    const bool farm = d.work == sim::WorkKind::Farm && b->state == sim::BuildingState::Complete;
    const float field_row = std::round(ctx.s(30.0f));
    const float button_h = std::round(ctx.s(34.0f));
    const float title_h = ctx.text().line_height(title);
    float h = pad + title_h + pad * 0.5f + static_cast<float>(lines.size()) * line;
    h += button_h + pad * 0.5f;  // The eye and the switch.
    const bool lists = mine && b->state == sim::BuildingState::Complete;
    if (lists) {
        h += people_height(ctx, b->residents.size()) + people_height(ctx, b->workers.size());
    }
    if (progress >= 0.0f) {
        h += ctx.s(14.0f);
    }
    if (has_workers) {
        h += button_h + pad * 0.5f;
    }
    const bool removable = window_entity_ != game.player(s.town()).town_center;
    if (removable) {
        h += button_h + pad * 0.5f;
    }
    if (farm) {
        h += static_cast<float>(b->fields.size()) * (line + field_row + pad * 0.5f) + button_h + pad;
    }
    const bool town_center = d.kind == sim::BuildingKind::TownCenter && b->state == sim::BuildingState::Complete;
    const bool workshop = d.work == sim::WorkKind::Produce && b->state == sim::BuildingState::Complete;
    if (town_center) {
        h += 2 * line + 2 * button_h + pad * 1.5f;
    }
    if (workshop) {
        h += button_h + pad * 0.5f;
    }
    const bool post = d.trade && b->state == sim::BuildingState::Complete;
    const bool barracks = d.trains && b->state == sim::BuildingState::Complete;
    if (barracks) {
        h += pad * 0.5f + field_row + static_cast<float>(content.units.size()) * field_row + ctx.s(14.0f);
    }
    if (post) {
        const std::size_t rows = game.merchant_here(s.town()) ? merchant_rows(game, s.town()).size() : 0;
        h += pad * 0.5f + button_h + pad * 0.5f + line + static_cast<float>(rows) * field_row;
        h += pad * 0.5f + auto_trade_height(ctx, game, s.town(), field_row);
    }
    h += pad;
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(h)};
    bool open = true;
    if (!window(ctx, s, o.id, tr(d.name_key), box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    ctx.push_id("building_window");
    float y = box.y + pad;
    y += title_h + pad * 0.5f;
    {
        // The eye takes the camera to it; the switch stops its work and
        // lets its workers go (it remembers how many it wanted).
        const float half = std::round((box.w - 2 * pad - ctx.s(6.0f)) * 0.5f);
        if (ctx.button(ctx.id("eye"), {box.x + pad, y, half, button_h}, tr("hud.window.eye"), tr("hud.window.eye.tooltip"))) {
            services_.focus_camera(static_cast<float>(b->x) + static_cast<float>(b->width) * 0.5f,
                                   static_cast<float>(b->z) + static_cast<float>(b->depth) * 0.5f);
        }
        if (has_workers && mine) {
            if (ctx.button(ctx.id("production"), {box.right() - pad - half, y, half, button_h},
                           tr(b->stopped ? "hud.building.stopped" : "hud.building.working"),
                           tr("hud.building.production.tooltip"), true, b->stopped)) {
                sim::Command c;
                c.type = sim::CommandType::SetProduction;
                c.entity = window_entity_;
                c.value = b->stopped ? 1 : 0;
                s.issue(c);
            }
        }
        y += button_h + pad * 0.5f;
    }
    if (progress >= 0.0f) {
        meter(ctx, {box.x + pad, y, box.w - 2 * pad, ctx.s(8.0f)}, progress, ctx.theme().accent);
        y += ctx.s(14.0f);
    }
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
    if (lists) {
        people_list(ctx, s, o, box, y, b->residents, "hud.building.residentList");
        people_list(ctx, s, o, box, y, b->workers, "hud.building.workerList");
    }
    if (has_workers) {
        y += pad * 0.5f;
        const std::string text = tr("hud.building.workers", static_cast<int>(b->workers.size()), b->wanted_workers, d.workers);
        ctx.label({box.x + pad, y, box.w - 2 * pad - 2 * button_h - ctx.s(8.0f), button_h}, text, body, ctx.theme().text);
        const auto set_workers = [&](std::int32_t n) {
            sim::Command c;
            c.type = sim::CommandType::SetWorkers;
            c.entity = window_entity_;
            c.value = n;
            s.issue(c);
        };
        const ui::Rect minus{box.right() - pad - 2 * button_h - ctx.s(4.0f), y, button_h, button_h};
        const ui::Rect plus{box.right() - pad - button_h, y, button_h, button_h};
        if (ctx.button(ctx.id("fewer"), minus, tr("hud.building.fewer"), tr("hud.building.fewer.tooltip"),
                       b->wanted_workers > 0)) {
            set_workers(b->wanted_workers - 1);
        }
        if (highlight_ == "workers") {
            mark(ctx, plus);
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
    if (post) {
        // How much gold to keep here, for buying (phase 28).
        y += pad * 0.5f;
        ctx.label({box.x + pad, y, box.w - 2 * pad - 2 * button_h - ctx.s(8.0f), button_h}, tr("hud.post.reserve", b->limit),
                  body, ctx.theme().text);
        const auto set_reserve = [&](std::int32_t n) {
            sim::Command c;
            c.type = sim::CommandType::SetLimit;
            c.entity = window_entity_;
            c.value = std::clamp(n, 0, 10000);
            s.issue(c);
        };
        if (ctx.button(ctx.id("reserve_less"), {box.right() - pad - 2 * button_h - ctx.s(4.0f), y, button_h, button_h},
                       tr("hud.building.fewer"), tr("hud.post.reserve.tooltip"), b->limit > 0)) {
            set_reserve(b->limit - 50);
        }
        if (ctx.button(ctx.id("reserve_more"), {box.right() - pad - button_h, y, button_h, button_h}, tr("hud.building.more"),
                       tr("hud.post.reserve.tooltip"), b->limit < d.storage)) {
            set_reserve(std::min(b->limit + 50, d.storage));
        }
        y += button_h + pad * 0.5f;
        merchant_section(ctx, s, box, y, field_row);
        y += pad * 0.5f;
        auto_trade_section(ctx, s, box, y, field_row);
    }
    if (barracks) {
        y += pad * 0.5f;
        barracks_section(ctx, s, *b, box, y, field_row);
    }
    if (workshop) {
        // How much of its product to keep: automatic, or a set amount.
        y += pad * 0.5f;
        const std::string text = b->limit > 0 ? tr("hud.building.limit", b->limit) : tr("hud.building.limitAuto");
        ctx.label({box.x + pad, y, box.w - 2 * pad - 2 * button_h - ctx.s(8.0f), button_h}, text, body, ctx.theme().text);
        const auto set_limit = [&](std::int32_t n) {
            sim::Command c;
            c.type = sim::CommandType::SetLimit;
            c.entity = window_entity_;
            c.value = std::clamp(n, 0, 10000);
            s.issue(c);
        };
        if (ctx.button(ctx.id("limit_less"), {box.right() - pad - 2 * button_h - ctx.s(4.0f), y, button_h, button_h},
                       tr("hud.building.fewer"), tr("hud.building.limit.tooltip"), b->limit > 0)) {
            set_limit(b->limit - 10);
        }
        if (ctx.button(ctx.id("limit_more"), {box.right() - pad - button_h, y, button_h, button_h},
                       tr("hud.building.more"), tr("hud.building.limit.tooltip"))) {
            set_limit(b->limit + 10);
        }
        y += button_h;
    }
    if (town_center) {
        y += pad * 0.5f;
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.tc.level", game.tier(b->owner)), body, ctx.theme().text);
        y += line;
        const bool has_next = b->level < d.levels.size();
        std::string req = tr("hud.tc.max");
        bool can = false;
        if (has_next) {
            const sim::LevelDef& next = d.levels[b->level];
            std::string cost;
            for (const sim::ResourceAmount& c : next.cost) {
                cost += (cost.empty() ? "" : ", ") + tr("hud.amount", tr(content.resources[c.resource].name_key), c.amount);
            }
            req = b->upgrading ? tr("hud.tc.upgrading") : tr("hud.tc.next", next.population, cost);
            can = !b->upgrading && game.population(b->owner) >= next.population;
        }
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, req, ctx.style(ctx.theme().small), ctx.theme().text_dim);
        y += line;
        if (ctx.button(ctx.id("tc_upgrade"), {box.x + pad, y, box.w - 2 * pad, button_h}, tr("hud.tc.upgrade"),
                       tr("hud.tc.upgrade.tooltip"), can)) {
            sim::Command c;
            c.type = sim::CommandType::UpgradeBuilding;
            c.entity = window_entity_;
            s.issue(c);
        }
        y += button_h + pad * 0.5f;
        // The bell: the militia.
        const bool alarm = game.player(b->owner).alarm;
        if (ctx.button(ctx.id("tc_bell"), {box.x + pad, y, box.w - 2 * pad, button_h},
                       tr(alarm ? "hud.bell.stop" : "hud.bell.ring"), tr("hud.bell.tooltip"), true, alarm)) {
            sim::Command c;
            c.type = sim::CommandType::RingBell;
            c.value = alarm ? 0 : 1;
            s.issue(c);
        }
        y += button_h;
    }
    if (removable) {
        y += pad * 0.5f;
        const bool building = b->state == sim::BuildingState::Construction;
        if (ctx.button(ctx.id("remove"), {box.x + pad, y, box.w - 2 * pad, button_h},
                       tr(building ? "hud.building.cancel" : "hud.building.demolish"),
                       tr(building ? "hud.building.cancel.tooltip" : "hud.building.demolish.tooltip"))) {
            sim::Command c;
            c.type = sim::CommandType::RemoveBuilding;
            c.entity = window_entity_;
            s.issue(c);
            closing_.push_back(o.id);
        }
    }
    ctx.pop_id();
}

void GameHud::barracks_section(ui::Context& ctx, GameSession& s, const sim::Building& b, const ui::Rect& box, float& y,
                               float row_h) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(14.0f);
    // What is being trained.
    std::string queue = tr("hud.barracks.idle");
    if (!b.training.empty() && b.training.front() < content.units.size()) {
        const sim::UnitDef& u = content.units[b.training.front()];
        queue = tr("hud.barracks.training", tr(u.name_key), static_cast<int>(b.training.size()));
    }
    const float bw = std::round(ctx.s(96.0f));
    ctx.label({box.x + pad, y, box.w - 2 * pad - bw - ctx.s(6.0f), row_h}, queue, body, ctx.theme().text);
    const ui::Rect cancel{box.right() - pad - bw, y + ctx.s(2.0f), bw, row_h - ctx.s(4.0f)};
    if (ctx.button(ctx.id("cancel"), cancel, tr("hud.barracks.cancel"), tr("hud.barracks.cancel.tooltip"),
                   !b.training.empty())) {
        sim::Command c;
        c.type = sim::CommandType::TrainUnit;
        c.entity = window_entity_;
        c.value = 0;
        s.issue(c);
    }
    y += row_h;
    if (!b.training.empty() && b.training.front() < content.units.size()) {
        const float done = static_cast<float>(b.train_progress) /
                           static_cast<float>(std::max(1, content.units[b.training.front()].train_work));
        meter(ctx, {box.x + pad, y + ctx.s(3.0f), box.w - 2 * pad, ctx.s(6.0f)}, done, ctx.theme().accent);
    }
    y += ctx.s(14.0f);
    for (std::size_t i = 0; i < content.units.size(); ++i) {
        const sim::UnitDef& u = content.units[i];
        std::string cost;
        for (const sim::ResourceAmount& c : u.cost) {
            cost += (cost.empty() ? "" : ", ") + tr("hud.amount", tr(content.resources[c.resource].name_key), c.amount);
        }
        ctx.push_id(u.id);
        const bool locked = u.tier > game.tier(b.owner);
        ctx.label({box.x + pad, y, box.w - 2 * pad - bw - ctx.s(6.0f), row_h},
                  locked ? tr("hud.barracks.locked", tr(u.name_key), static_cast<int>(u.tier))
                         : tr("hud.barracks.unit", tr(u.name_key), cost),
                  small, locked ? ctx.theme().text_dim : ctx.theme().text);
        const auto order = [&](std::int32_t value) {
            sim::Command c;
            c.type = sim::CommandType::TrainUnit;
            c.entity = window_entity_;
            c.def = static_cast<sim::DefIndex>(i);
            c.value = value;
            s.issue(c);
        };
        const ui::Rect train{box.right() - pad - bw, y + ctx.s(2.0f), bw, row_h - ctx.s(4.0f)};
        if (ctx.button(ctx.id("train"), train, tr("hud.barracks.train"),
                       tr("hud.barracks.train.tooltip", u.health, u.damage, u.range), !locked && b.training.size() < 10)) {
            order(1);
        }
        ctx.pop_id();
        y += row_h;
    }
}

void GameHud::army_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const std::uint8_t town = s.town();
    const sim::PlayerState& ps = game.player(town);
    const sim::GameRules& rules = game.rules();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float row = std::round(ctx.s(34.0f));
    const float gap = ctx.s(6.0f);
    const float w = std::min(ctx.s(420.0f), ctx.width() - 2 * pad);

    std::vector<std::uint8_t> enemies;
    std::vector<std::string> enemy_names;
    std::vector<std::uint8_t> towns;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_of(p) != p || !game.player(p).active) {
            continue;
        }
        towns.push_back(p);
        if (game.enemies(town, p) && game.buildings().get(game.player(p).town_center) != nullptr) {
            enemies.push_back(p);
            enemy_names.push_back(town_name(p));
        }
    }
    const float title_h = ctx.text().line_height(title);
    float h = pad + title_h + pad * 0.5f + 2 * line + gap;
    h += 3 * (row + gap);  // Defend, defend here, retreat.
    h += enemies.empty() ? line : row + gap + row;
    h += pad + line + static_cast<float>(towns.size()) * line + pad;
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(w), std::round(h)};
    bool open = true;
    if (!window(ctx, s, "army", tr("hud.army.title"), box, open)) {
        army_open_ = open;
        return;
    }
    army_open_ = open;
    ctx.push_id("army_window");
    float y = box.y + pad;
    y += title_h + pad * 0.5f;
    ctx.label({box.x + pad, y, box.w - 2 * pad, line},
              tr("hud.army.strength", game.soldiers(town), game.military_power(town)), body, ctx.theme().text);
    y += line;
    static constexpr const char* kOrders[] = {"hud.army.order.defend", "hud.army.order.attack", "hud.army.order.retreat"};
    std::string order = tr(kOrders[static_cast<std::size_t>(ps.order) % 3]);
    if (ps.order == sim::ArmyOrderKind::Attack) {
        order = tr("hud.army.order.attacking", town_name(ps.enemy));
    }
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, order, small, ctx.theme().text_dim);
    y += line + gap;
    const auto issue = [&](std::int32_t value, std::uint8_t enemy, sim::FixedVec2 at) {
        sim::Command c;
        c.type = sim::CommandType::ArmyOrder;
        c.value = value;
        c.count = enemy;
        c.position = at;
        s.issue(c);
    };
    const ui::Rect full{box.x + pad, y, box.w - 2 * pad, row};
    if (ctx.button(ctx.id("defend"), full, tr("hud.army.defend"), tr("hud.army.defend.tooltip"))) {
        issue(0, 0, {});
    }
    y += row + gap;
    if (ctx.button(ctx.id("defend_here"), {box.x + pad, y, box.w - 2 * pad, row}, tr("hud.army.defendHere"),
                   tr("hud.army.defendHere.tooltip"), true, s.ui().rally_mode)) {
        s.ui().rally_mode = !s.ui().rally_mode;
    }
    y += row + gap;
    if (ctx.button(ctx.id("retreat"), {box.x + pad, y, box.w - 2 * pad, row}, tr("hud.army.retreat"),
                   tr("hud.army.retreat.tooltip"))) {
        issue(2, 0, {});
    }
    y += row + gap;
    if (enemies.empty()) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line},
                  tr(rules.versus && rules.pvp ? "hud.army.noEnemies" : "hud.army.peace"), small, ctx.theme().text_dim);
        y += line;
    } else {
        attack_pick_ = std::clamp(attack_pick_, 0, static_cast<int>(enemies.size()) - 1);
        ctx.selector(ctx.id("enemy"), {box.x + pad, y, box.w - 2 * pad, row}, attack_pick_, enemy_names);
        y += row + gap;
        if (ctx.button(ctx.id("attack"), {box.x + pad, y, box.w - 2 * pad, row}, tr("hud.army.attack"),
                       tr("hud.army.attack.tooltip"), game.soldiers(town) > 0)) {
            issue(1, enemies[static_cast<std::size_t>(attack_pick_)], {});
        }
        y += row;
    }
    y += pad;
    // The scores.
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.army.scores"), body, ctx.theme().text);
    y += line;
    static constexpr const char* kOutcomes[] = {"hud.outcome.playing", "hud.outcome.won", "hud.outcome.lost"};
    for (const std::uint8_t p : towns) {
        const sim::PlayerState& other = game.player(p);
        ctx.label({box.x + pad, y, box.w - 2 * pad, line},
                  tr("hud.army.scoreRow", town_name(p), game.score(p), game.military_power(p),
                     tr(kOutcomes[static_cast<std::size_t>(other.outcome) % 3])),
                  small, p == town ? ctx.theme().accent : ctx.theme().text);
        y += line;
    }
    ctx.pop_id();
}

std::string GameHud::town_name(std::uint8_t player) const {
    if (net::NetSession* net = services_.net()) {
        for (const net::LobbyPlayer& p : net->lobby().players) {
            if (p.slot == player) {
                return p.name;
            }
        }
    }
    return tr("hud.trade.town", static_cast<int>(player) + 1);
}

std::string GameHud::goods_name(const sim::Game& game, sim::DefIndex r) const {
    return r < game.content().resources.size() ? tr(game.content().resources[r].name_key) : std::string();
}

// What the merchant sells, and what the town has to sell him.
std::vector<sim::DefIndex> GameHud::merchant_rows(const sim::Game& game, std::uint8_t town) const {
    std::vector<sim::DefIndex> rows;
    for (const sim::MerchantGood& m : game.player(town).merchant) {
        if ((m.stock > 0 || (m.sell > 0 && game.tradeable(town, m.resource) >= 10)) && rows.size() < 14) {
            rows.push_back(m.resource);
        }
    }
    return rows;
}

void GameHud::merchant_section(ui::Context& ctx, GameSession& s, const ui::Rect& box, float& y, float row_h) {
    const sim::Game& game = s.game();
    const std::uint8_t town = s.town();
    const sim::PlayerState& ps = game.player(town);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float line = ctx.text().line_height(body);
    const float pad = ctx.s(14.0f);
    if (!game.merchant_here(town)) {
        const std::uint64_t next = ps.merchant_arrives > game.tick() ? ps.merchant_arrives - game.tick() : 0;
        const auto days = static_cast<int>((next + game.calendar_day_ticks() - 1) / game.calendar_day_ticks());
        ctx.label({box.x + pad, y, box.w - 2 * pad, line},
                  ps.merchant_arrives == 0 ? tr("hud.merchant.none") : tr("hud.merchant.next", days), body,
                  ctx.theme().text_dim);
        y += line;
        return;
    }
    const std::uint64_t left = ps.merchant_leaves - game.tick();
    ctx.label({box.x + pad, y, box.w - 2 * pad, line},
              tr("hud.merchant.here", static_cast<int>((left + game.calendar_day_ticks() - 1) / game.calendar_day_ticks())), body,
              ctx.theme().accent);
    y += line;
    const float bw = std::round(ctx.s(74.0f));
    for (const sim::DefIndex r : merchant_rows(game, town)) {
        const sim::MerchantGood* m = nullptr;
        for (const sim::MerchantGood& g : ps.merchant) {
            m = g.resource == r ? &g : m;
        }
        if (m == nullptr) {
            continue;
        }
        const std::int32_t have = game.tradeable(town, r);
        const std::int32_t buy = std::min(10, m->stock);
        const std::int32_t sell = std::min(10, have);
        ctx.push_id(std::to_string(r));
        ctx.label({box.x + pad, y, box.w - 2 * pad - 2 * bw - ctx.s(8.0f), row_h},
                  tr("hud.merchant.row", goods_name(game, r), have, m->stock), small, ctx.theme().text);
        const auto trade = [&](std::int32_t n) {
            sim::Command c;
            c.type = sim::CommandType::Trade;
            c.entity = window_entity_;
            c.def = r;
            c.value = n;
            s.issue(c);
        };
        const ui::Rect buy_r{box.right() - pad - 2 * bw - ctx.s(4.0f), y + ctx.s(2.0f), bw, row_h - ctx.s(4.0f)};
        const ui::Rect sell_r{box.right() - pad - bw, y + ctx.s(2.0f), bw, row_h - ctx.s(4.0f)};
        if (ctx.button(ctx.id("buy"), buy_r, tr("hud.merchant.buy"), tr("hud.merchant.buy.tooltip", buy, buy * m->buy),
                       buy > 0 && game.gold(town) >= buy * m->buy)) {
            trade(buy);
        }
        if (ctx.button(ctx.id("sell"), sell_r, tr("hud.merchant.sell"),
                       tr("hud.merchant.sell.tooltip", sell, sell * m->sell), sell > 0 && m->sell > 0)) {
            trade(-sell);
        }
        ctx.pop_id();
        y += row_h;
    }
}

namespace {

// The goods merchants trade, which automatic trade can name.
std::vector<sim::DefIndex> rule_goods(const sim::Content& content) {
    std::vector<sim::DefIndex> out;
    for (std::size_t r = 0; r < content.resources.size(); ++r) {
        if (content.resources[r].value > 0) {
            out.push_back(static_cast<sim::DefIndex>(r));
        }
    }
    return out;
}

}  // namespace

float GameHud::auto_trade_height(ui::Context& ctx, const sim::Game& game, std::uint8_t town, float row_h) const {
    const float line = ctx.text().line_height(ctx.style(ctx.theme().body));
    const float small = ctx.text().line_height(ctx.style(ctx.theme().small));
    const std::size_t rules = std::min<std::size_t>(game.player(town).trade_rules.size(), 8);
    return 2 * line + 6 * row_h + static_cast<float>(rules) * small;
}

// "Sell over N, buy under M" for one good at a time, applied with a
// button; the rules in force listed below.
void GameHud::auto_trade_section(ui::Context& ctx, GameSession& s, const ui::Rect& box, float& y, float row_h) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const std::uint8_t town = s.town();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float line = ctx.text().line_height(body);
    const float small_line = ctx.text().line_height(small);
    const float pad = ctx.s(14.0f);
    const std::vector<sim::DefIndex> goods = rule_goods(content);
    const std::vector<sim::TradeRule>& rules = game.player(town).trade_rules;
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.auto.title"), body, ctx.theme().text);
    ctx.tooltip_area(ctx.id("auto_title"), {box.x + pad, y, box.w - 2 * pad, line}, tr("hud.auto.tooltip"));
    y += line;
    if (goods.empty()) {
        y += line + 6 * row_h;
        return;
    }
    std::vector<std::string> names;
    for (const sim::DefIndex r : goods) {
        names.push_back(tr(content.resources[r].name_key));
    }
    rule_pick_ = std::clamp(rule_pick_, 0, static_cast<int>(goods.size()) - 1);
    const sim::DefIndex picked = goods[static_cast<std::size_t>(rule_pick_)];
    const sim::TradeRule* current = nullptr;
    for (const sim::TradeRule& rule : rules) {
        current = rule.resource == picked ? &rule : current;
    }
    if (rule_loaded_ != rule_pick_) {
        // A new good: show its rule, or none.
        rule_loaded_ = rule_pick_;
        rule_sell_ = current != nullptr && current->sell_above != sim::kNoRule ? current->sell_above : -10;
        rule_buy_ = current != nullptr && current->buy_below != sim::kNoRule ? current->buy_below : -10;
        rule_sell_min_ = current != nullptr && current->sell_min != 0 ? current->sell_min : 70;
        rule_buy_max_ = current != nullptr && current->buy_max != 0 ? current->buy_max : 70;
    }
    const float x = box.x + pad;
    const float w = box.w - 2 * pad;
    const float gap = ctx.s(4.0f);
    ctx.push_id("auto_trade");
    ctx.selector(ctx.id("good"), {x, y + gap / 2, w, row_h - gap}, rule_pick_, names);
    y += row_h;
    const auto shown = [&](const char* key) {
        return [key](int v) { return v < 0 ? tr("hud.auto.off") : tr(key, v); };
    };
    ctx.slider(ctx.id("sell"), {x, y + gap / 2, w, row_h - gap}, rule_sell_, -10, 2000, 10, shown("hud.auto.sell"),
               tr("hud.auto.sell.tooltip"));
    y += row_h;
    // Only at a good price: over a share of the good's value when selling.
    const auto price = [&](const char* key) {
        return [key](int v) { return v < sim::kMinPriceLimit ? tr("hud.auto.anyPrice") : tr(key, v); };
    };
    ctx.slider(ctx.id("sell_min"), {x, y + gap / 2, w, row_h - gap}, rule_sell_min_, 70, sim::kMaxPriceLimit, 5,
               price("hud.auto.sellMin"), tr("hud.auto.sellMin.tooltip"), rule_sell_ >= 0);
    y += row_h;
    ctx.slider(ctx.id("buy"), {x, y + gap / 2, w, row_h - gap}, rule_buy_, -10, 2000, 10, shown("hud.auto.buy"),
               tr("hud.auto.buy.tooltip"));
    y += row_h;
    ctx.slider(ctx.id("buy_max"), {x, y + gap / 2, w, row_h - gap}, rule_buy_max_, 70, sim::kMaxPriceLimit, 5,
               price("hud.auto.buyMax"), tr("hud.auto.buyMax.tooltip"), rule_buy_ >= 0);
    y += row_h;
    const std::int32_t sell = rule_sell_ < 0 ? sim::kNoRule : rule_sell_;
    const std::int32_t buy = rule_buy_ < 0 ? sim::kNoRule : rule_buy_;
    const bool valid = sell == sim::kNoRule || buy == sim::kNoRule || buy <= sell;
    const int sell_min = sell == sim::kNoRule || rule_sell_min_ < sim::kMinPriceLimit ? 0 : rule_sell_min_;
    const int buy_max = buy == sim::kNoRule || rule_buy_max_ < sim::kMinPriceLimit ? 0 : rule_buy_max_;
    const bool same = current != nullptr ? current->sell_above == sell && current->buy_below == buy &&
                                               current->sell_min == sell_min && current->buy_max == buy_max
                                         : sell == sim::kNoRule && buy == sim::kNoRule;
    if (ctx.button(ctx.id("apply"), {x, y + gap / 2, w, row_h - gap}, tr("hud.auto.apply"),
                   valid ? tr("hud.auto.apply.tooltip") : tr("hud.auto.apply.invalid"), valid && !same)) {
        sim::Command c;
        c.type = sim::CommandType::SetTradeRule;
        c.def = picked;
        c.value = sell;
        c.value2 = buy;
        c.count = static_cast<std::uint16_t>(sell_min);
        c.def2 = static_cast<std::uint16_t>(buy_max);
        s.issue(c);
    }
    y += row_h;
    ctx.pop_id();
    // The rules in force.
    ctx.label({x, y, w, line}, tr(rules.empty() ? "hud.auto.none" : "hud.auto.rules"), body, ctx.theme().text_dim);
    y += line;
    for (std::size_t i = 0; i < rules.size() && i < 8; ++i) {
        const sim::TradeRule& rule = rules[i];
        std::string parts;
        if (rule.sell_above != sim::kNoRule) {
            parts = tr("hud.auto.sell", rule.sell_above);
            if (rule.sell_min != 0) {
                parts += " (" + tr("hud.auto.sellMin", static_cast<int>(rule.sell_min)) + ")";
            }
        }
        if (rule.buy_below != sim::kNoRule) {
            parts += (parts.empty() ? "" : " · ") + tr("hud.auto.buy", rule.buy_below);
            if (rule.buy_max != 0) {
                parts += " (" + tr("hud.auto.buyMax", static_cast<int>(rule.buy_max)) + ")";
            }
        }
        const std::string name = rule.resource < content.resources.size() ? tr(content.resources[rule.resource].name_key)
                                                                          : std::string();
        ctx.label({x, y, w, small_line}, tr("hud.auto.rule", name, parts), small, ctx.theme().text);
        y += small_line;
    }
}

void GameHud::trade_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const std::uint8_t town = s.town();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float row = std::round(ctx.s(34.0f));
    const float gap = ctx.s(6.0f);
    const float w = std::min(ctx.s(440.0f), ctx.width() - 2 * pad);

    // Who can be traded with, and what.
    std::vector<std::uint8_t> towns;
    std::vector<std::string> town_names;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_of(p) == p && p != town && game.player(p).active) {
            towns.push_back(p);
            town_names.push_back(town_name(p));
        }
    }
    if (towns.empty()) {
        trade_open_ = false;
        return;
    }
    // Gold first, then the goods merchants trade.
    std::vector<sim::DefIndex> goods;
    std::vector<std::string> goods_names;
    if (game.gold() != sim::kNoDef) {
        goods.push_back(game.gold());
        goods_names.push_back(tr(game.content().resources[game.gold()].name_key));
    }
    for (std::size_t r = 0; r < game.content().resources.size(); ++r) {
        if (game.content().resources[r].value > 0) {
            goods.push_back(static_cast<sim::DefIndex>(r));
            goods_names.push_back(tr(game.content().resources[r].name_key));
        }
    }
    offer_to_ = std::clamp(offer_to_, 0, static_cast<int>(towns.size()) - 1);
    offer_give_ = std::clamp(offer_give_, 0, static_cast<int>(goods.size()) - 1);
    offer_want_ = std::clamp(offer_want_, 0, static_cast<int>(goods.size()) - 1);
    std::vector<const sim::TradeOffer*> offers;
    for (const sim::TradeOffer& o : game.offers()) {
        if (o.from == town || o.to == town) {
            offers.push_back(&o);
        }
    }
    std::vector<const sim::Caravan*> caravans;
    for (const sim::Caravan& c : game.caravans()) {
        if ((c.from == town || c.to == town) && caravans.size() < 8) {
            caravans.push_back(&c);
        }
    }
    const std::int32_t region = game.map().region_size();
    const float map_side = region > 0 ? std::round(ctx.s(150.0f)) : 0.0f;
    const float title_h = ctx.text().line_height(title);
    float h = pad + title_h + pad * 0.5f;
    h += map_side > 0 ? map_side + pad : 0.0f;
    h += line + 3 * (row + gap) + row + pad;  // The new offer.
    h += line + static_cast<float>(offers.size()) * (row + gap) + pad * 0.5f;
    h += line + static_cast<float>(caravans.size()) * line + pad;
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(w), std::round(h)};
    bool open = true;
    if (!window(ctx, s, "trade", tr("hud.trade.title"), box, open)) {
        trade_open_ = open;
        return;
    }
    trade_open_ = open;
    ctx.push_id("trade_window");
    float y = box.y + pad;
    y += title_h + pad * 0.5f;

    // The world map: one square per player's map, caravans on the way.
    if (map_side > 0) {
        const std::int32_t k = game.map().size / region;
        const float cell = map_side / static_cast<float>(k);
        const float mx = box.x + (box.w - map_side) * 0.5f;
        const auto center = [&](std::uint8_t p) {
            return std::pair<float, float>{mx + (static_cast<float>(p % k) + 0.5f) * cell,
                                           y + (static_cast<float>(p / k) + 0.5f) * cell};
        };
        for (std::int32_t i = 0; i < k * k; ++i) {
            const ui::Rect r{mx + static_cast<float>(i % k) * cell + 2, y + static_cast<float>(i / k) * cell + 2, cell - 4,
                             cell - 4};
            const bool used = i < game.player_count() && game.player(static_cast<std::uint8_t>(i)).active;
            ctx.draw().rect(r, !used ? ui::Color::rgb(0x2A4A66) : i == town ? ctx.theme().accent.with_alpha(0.8f)
                                                                            : ui::Color::rgb(0x5F7F3F));
            if (used) {
                ctx.label(r, std::to_string(i + 1), small, ctx.theme().text, ui::Align::Center);
            }
        }
        for (const sim::Caravan& c : game.caravans()) {
            const float t = c.arrives > c.departs ? static_cast<float>(game.tick() - c.departs) /
                                                        static_cast<float>(c.arrives - c.departs)
                                                  : 1.0f;
            const auto [ax, az] = center(c.from);
            const auto [bx, bz] = center(c.to);
            const float px = ax + (bx - ax) * std::clamp(t, 0.0f, 1.0f);
            const float pz = az + (bz - az) * std::clamp(t, 0.0f, 1.0f);
            const float dot = ctx.s(6.0f);
            ctx.draw().rect({px - dot * 0.5f, pz - dot * 0.5f, dot, dot}, ui::Color::rgb(0xE8C45A));
        }
        ctx.tooltip_area(ctx.id("world_map"), {mx, y, map_side, map_side}, tr("hud.trade.worldMap"));
        y += map_side + pad;
    }

    // A new offer.
    const float label_w = std::round(ctx.s(80.0f));
    const float amount_w = std::round(ctx.s(120.0f));
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.trade.new"), body, ctx.theme().text);
    y += line;
    ctx.label({box.x + pad, y, label_w, row}, tr("hud.trade.to"), small, ctx.theme().text_dim);
    ctx.selector(ctx.id("to"), {box.x + pad + label_w, y, box.w - 2 * pad - label_w, row}, offer_to_, town_names);
    y += row + gap;
    const float pick_w = box.w - 2 * pad - label_w - amount_w - gap;
    ctx.label({box.x + pad, y, label_w, row}, tr("hud.trade.give"), small, ctx.theme().text_dim);
    ctx.selector(ctx.id("give"), {box.x + pad + label_w, y, pick_w, row}, offer_give_, goods_names);
    ctx.slider(ctx.id("give_n"), {box.right() - pad - amount_w, y, amount_w, row}, offer_give_amount_, 10, 500, 10,
               [](int v) { return std::to_string(v); });
    y += row + gap;
    ctx.label({box.x + pad, y, label_w, row}, tr("hud.trade.want"), small, ctx.theme().text_dim);
    ctx.selector(ctx.id("want"), {box.x + pad + label_w, y, pick_w, row}, offer_want_, goods_names);
    ctx.slider(ctx.id("want_n"), {box.right() - pad - amount_w, y, amount_w, row}, offer_want_amount_, 10, 500, 10,
               [](int v) { return std::to_string(v); });
    y += row + gap;
    const sim::DefIndex give = goods[static_cast<std::size_t>(offer_give_)];
    const sim::DefIndex want = goods[static_cast<std::size_t>(offer_want_)];
    const std::int32_t have = game.tradeable(town, give);
    const bool can = give != want && have >= offer_give_amount_;
    if (ctx.button(ctx.id("send"), {box.x + pad, y, box.w - 2 * pad, row}, tr("hud.trade.send"),
                   can ? tr("hud.trade.send.tooltip") : tr("hud.trade.send.cannot", have), can)) {
        sim::Command c;
        c.type = sim::CommandType::OfferTrade;
        c.count = towns[static_cast<std::size_t>(offer_to_)];
        c.def = give;
        c.value = offer_give_amount_;
        c.def2 = want;
        c.value2 = offer_want_amount_;
        s.issue(c);
    }
    y += row + pad;

    // Offers made and received.
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr(offers.empty() ? "hud.trade.noOffers" : "hud.trade.offers"), body,
              ctx.theme().text);
    y += line;
    const float bw = std::round(ctx.s(96.0f));
    for (const sim::TradeOffer* o : offers) {
        ctx.push_id(std::to_string(o->id));
        const bool mine = o->from == town;
        const std::string what = mine ? tr("hud.trade.offerOut", town_name(o->to), o->give_amount, goods_name(game, o->give),
                                           o->want_amount, goods_name(game, o->want))
                                      : tr("hud.trade.offerIn", town_name(o->from), o->give_amount,
                                           goods_name(game, o->give), o->want_amount, goods_name(game, o->want));
        const float buttons = mine ? bw : 2 * bw + gap;
        ctx.label({box.x + pad, y, box.w - 2 * pad - buttons - gap, row}, what, small, ctx.theme().text);
        const auto answer = [&](std::uint16_t yes) {
            sim::Command c;
            c.type = sim::CommandType::AnswerOffer;
            c.value = static_cast<std::int32_t>(o->id);
            c.count = yes;
            s.issue(c);
        };
        if (mine) {
            if (ctx.button(ctx.id("withdraw"), {box.right() - pad - bw, y, bw, row}, tr("hud.trade.withdraw"))) {
                answer(0);
            }
        } else {
            const std::int32_t mine_have = game.tradeable(town, o->want);
            if (ctx.button(ctx.id("accept"), {box.right() - pad - 2 * bw - gap, y, bw, row}, tr("hud.trade.accept"),
                           tr("hud.trade.accept.tooltip", static_cast<int>(game.travel_ticks(o->from, o->to) / game.calendar_day_ticks())),
                           mine_have >= o->want_amount)) {
                answer(1);
            }
            if (ctx.button(ctx.id("decline"), {box.right() - pad - bw, y, bw, row}, tr("hud.trade.decline"))) {
                answer(0);
            }
        }
        ctx.pop_id();
        y += row + gap;
    }
    y += pad * 0.5f;
    // Caravans on the way.
    ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr(caravans.empty() ? "hud.trade.noCaravans" : "hud.trade.caravans"),
              body, ctx.theme().text);
    y += line;
    for (const sim::Caravan* c : caravans) {
        const std::uint64_t left = c->arrives > game.tick() ? c->arrives - game.tick() : 0;
        const auto days = static_cast<int>((left + game.calendar_day_ticks() - 1) / game.calendar_day_ticks());
        const std::string text = c->to == town ? tr("hud.trade.caravanIn", c->amount, goods_name(game, c->resource),
                                                    town_name(c->from), days)
                                               : tr("hud.trade.caravanOut", c->amount, goods_name(game, c->resource),
                                                    town_name(c->to), days);
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, text, small, ctx.theme().text_dim);
        y += line;
    }
    ctx.pop_id();
}

void GameHud::house_lines(const sim::Game& game, const sim::Building& b, std::vector<std::string>& lines) const {
    const sim::BuildingDef& d = game.content().buildings[b.def];
    lines.push_back(tr("hud.house.level", static_cast<int>(b.level) + 1, static_cast<int>(d.levels.size()) + 1));
    lines.push_back(tr("hud.house.happiness", b.happiness, b.desirability));
    if (b.upgrading) {
        lines.push_back(tr("hud.house.upgrading"));
    } else if (b.level < d.levels.size()) {
        // What the next level still needs.
        const sim::LevelDef& next = d.levels[b.level];
        std::string missing;
        for (std::uint8_t n = 0; n < static_cast<std::uint8_t>(sim::Need::Count); ++n) {
            const bool needed = ((next.needs >> n) & 1u) != 0;
            const bool met = ((b.needs >> n) & 1u) != 0;
            if (needed && !met) {
                missing += (missing.empty() ? "" : ", ") + tr(need_text_key(n));
            }
        }
        if (next.tier > game.tier(b.owner)) {
            missing += (missing.empty() ? "" : ", ") + tr("hud.house.needsTier", next.tier);
        }
        lines.push_back(missing.empty() ? tr("hud.house.readyToGrow") : tr("hud.house.missing", missing));
    }
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
                c.entity = window_entity_;
                c.def = next;
                c.value = static_cast<std::int32_t>(i) | static_cast<std::int32_t>(year << 8);
                s.issue(c);
            }
        }
        if (ctx.button(ctx.id("remove"), {box.right() - pad - row_h, y, row_h, row_h}, tr("hud.close"),
                       tr("hud.farm.remove.tooltip"))) {
            sim::Command c;
            c.type = sim::CommandType::RemoveField;
            c.entity = window_entity_;
            c.value = static_cast<std::int32_t>(i);
            s.issue(c);
        }
        ctx.pop_id();
        y += row_h + pad * 0.5f;
    }
    const bool room = static_cast<std::int32_t>(b.fields.size()) < content.buildings[b.def].fields;
    const float button_h = std::round(ctx.s(34.0f));
    if (ctx.button(ctx.id("new_field"), {box.x + pad, y, box.w - 2 * pad, button_h}, tr("hud.farm.newField"),
                   tr(room ? "hud.farm.newField.tooltip" : "hud.farm.full"), room, ui.field_farm == window_entity_)) {
        ui.field_farm = window_entity_;
        ui.placing = sim::kNoDef;
    }
    y += button_h;
}

float GameHud::people_height(ui::Context& ctx, std::size_t count) const {
    if (count == 0) {
        return 0.0f;
    }
    const float row = std::round(ctx.s(28.0f)) + ctx.s(3.0f);
    return ctx.s(14.0f) * 0.5f + ctx.text().line_height(ctx.style(ctx.theme().small)) +
           static_cast<float>(std::min(count, kPeopleRows)) * row;
}

void GameHud::people_list(ui::Context& ctx, GameSession& s, const WindowList::Object& o, const ui::Rect& box, float& y,
                          const std::vector<sim::EntityId>& people, const char* title_key) {
    if (people.empty()) {
        return;
    }
    const sim::Game& game = s.game();
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(14.0f);
    const float row_h = std::round(ctx.s(28.0f));
    const float row = row_h + ctx.s(3.0f);
    y += pad * 0.5f;
    ctx.label({box.x + pad, y, box.w - 2 * pad, ctx.text().line_height(small)},
              tr(title_key, static_cast<int>(people.size())), small, ctx.theme().text_dim);
    y += ctx.text().line_height(small);
    const float shown_h = static_cast<float>(std::min(people.size(), kPeopleRows)) * row;
    const ui::Rect view{box.x + pad, y, box.w - 2 * pad, shown_h};
    const bool scrolls = people.size() > kPeopleRows;
    ctx.push_id(title_key);
    float top = scrolls ? ctx.begin_scroll(ctx.id("scroll"), view) : y;
    for (std::size_t k = 0; k < people.size(); ++k) {
        const sim::Villager* v = game.villagers().get(people[k]);
        if (v == nullptr) {
            continue;
        }
        std::string name = game.villager_name(*v);
        if (name.empty()) {
            name = tr(v->sex == sim::Sex::Female ? "hud.villager.woman" : "hud.villager.man");
        }
        // The id is the villager's own: the rows move as people come and go.
        if (ctx.button(ctx.id("v" + std::to_string(people[k].index)),
                       {view.x, top, view.w - (scrolls ? ctx.s(12.0f) : 0.0f), row_h},
                       tr("hud.villager.listed", name, game.age_years(*v)), tr("hud.villager.open.tooltip"))) {
            open_link(o.id, WindowList::Kind::Villager, people[k]);
        }
        top += row;
    }
    if (scrolls) {
        ctx.end_scroll(static_cast<float>(people.size()) * row);
    }
    ctx.pop_id();
    y += shown_h;
}

void GameHud::open_link(const std::string& from, WindowList::Kind kind, sim::EntityId entity) {
    links_.push_back({from, kind, entity});
}

void GameHud::villager_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    GameSession::Interaction& ui = s.ui();
    const sim::Villager* v = game.villagers().get(o.entity);
    if (v == nullptr) {
        gone_window(ctx, s, o);
        return;
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float pad = ctx.s(14.0f);
    const float gap = ctx.s(6.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    const std::int32_t age = game.age_years(*v);
    const bool mine = v->owner == s.town();
    const bool female = v->sex == sim::Sex::Female;
    const char* kind_key = !game.adult(*v) ? (female ? "hud.villager.girl" : "hud.villager.boy")
                                           : (female ? "hud.villager.woman" : "hud.villager.man");
    std::string name = game.villager_name(*v);
    if (name.empty()) {
        name = tr(kind_key);
    }
    const sim::Building* home = game.buildings().get(v->home);
    const sim::Building* job = game.buildings().get(v->job);

    std::vector<std::string> lines;
    lines.push_back(tr("hud.villager.who", tr(kind_key), age));
    if (v->race < content.races.size()) {
        lines.push_back(tr("hud.villager.race", tr(content.races[v->race].name_key)));
    }
    lines.push_back(tr("hud.villager.task", tr(task_text_key(v->task))));
    if (job == nullptr) {
        lines.push_back(tr(game.adult(*v) ? "hud.villager.laborer" : "hud.villager.child"));
    }
    if (home == nullptr) {
        lines.push_back(tr("hud.villager.homeless"));
    }
    lines.push_back(tr(v->clothes > 0 ? "hud.villager.clothes" : "hud.villager.noClothes"));
    if (v->disease != 0 && v->disease <= content.diseases.size()) {
        lines.push_back(tr("hud.villager.sick", tr(content.diseases[v->disease - 1u].name_key), v->sick_days));
    }
    if (v->carrying.amount > 0 && v->carrying.resource < content.resources.size()) {
        lines.push_back(tr("hud.villager.carrying", tr("hud.amount", tr(content.resources[v->carrying.resource].name_key),
                                                       v->carrying.amount)));
    }
    const bool renaming = rename_id_ == o.id && mine;
    const float bar_block = 3 * (line + ctx.s(10.0f));
    const float title_h = ctx.text().line_height(title);
    const float button_h = std::round(ctx.s(34.0f));
    const float link_h = std::round(ctx.s(30.0f));
    const float links = (home != nullptr ? link_h + ctx.s(3.0f) : 0.0f) + (job != nullptr ? link_h + ctx.s(3.0f) : 0.0f);
    const float h = pad + title_h + pad * 0.5f + button_h + pad * 0.5f + (renaming ? button_h + pad * 0.5f : 0.0f) +
                    static_cast<float>(lines.size()) * line + (links > 0.0f ? pad * 0.25f + links : 0.0f) + bar_block + pad;
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(h)};
    bool open = true;
    if (!window(ctx, s, o.id, name, box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    ctx.push_id("villager_window");
    float y = box.y + pad;
    y += title_h + pad * 0.5f;
    // The eye, following (a double click on it does the same) and its name.
    {
        const float third = std::round((box.w - 2 * pad - 2 * gap) / 3.0f);
        if (ctx.button(ctx.id("eye"), {box.x + pad, y, third, button_h}, tr("hud.window.eye"), tr("hud.window.eye.tooltip"))) {
            services_.focus_camera(meters(v->position.x), meters(v->position.z));
        }
        const bool followed = ui.followed_villager == o.entity;
        if (ctx.button(ctx.id("follow"), {box.x + pad + third + gap, y, third, button_h},
                       tr(followed ? "hud.villager.unfollow" : "hud.villager.follow"), tr("hud.villager.follow.tooltip"),
                       true, followed)) {
            ui.followed_villager = followed ? sim::EntityId{} : o.entity;
        }
        if (ctx.button(ctx.id("rename"), {box.right() - pad - third, y, third, button_h}, tr("hud.villager.rename"),
                       tr("hud.villager.rename.tooltip"), mine, renaming)) {
            rename_id_ = renaming ? std::string{} : o.id;
            rename_text_ = name;
        }
        y += button_h + pad * 0.5f;
    }
    if (renaming) {
        const float ok_w = std::round(ctx.s(64.0f));
        (void)ctx.text_field(ctx.id("name"), {box.x + pad, y, box.w - 2 * pad - ok_w - gap, button_h}, rename_text_,
                             sim::kMaxNameBytes, tr("hud.villager.name.tooltip"));
        // Spaces at the ends are not part of a name.
        std::string wanted = rename_text_;
        while (!wanted.empty() && wanted.back() == ' ') {
            wanted.pop_back();
        }
        wanted.erase(0, wanted.find_first_not_of(' ') == std::string::npos ? wanted.size() : wanted.find_first_not_of(' '));
        const bool valid = sim::valid_villager_name(wanted);
        const bool enter = ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_KP_ENTER);
        if ((ctx.button(ctx.id("name_ok"), {box.right() - pad - ok_w, y, ok_w, button_h}, tr("hud.villager.name.ok"),
                        tr("hud.villager.name.ok.tooltip"), valid) ||
             (enter && !ctx.input_blocked())) &&
            valid) {
            sim::Command c;
            c.type = sim::CommandType::RenameVillager;
            c.entity = o.entity;
            c.text = wanted;
            s.issue(c);
            rename_id_.clear();
        }
        y += button_h + pad * 0.5f;
    }
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
    // Its home and its workplace: a click opens that building's window.
    if (links > 0.0f) {
        y += pad * 0.25f;
        const auto link = [&](const char* id, const char* key, const sim::Building& b, sim::EntityId building) {
            if (ctx.button(ctx.id(id), {box.x + pad, y, box.w - 2 * pad, link_h},
                           tr(key, tr(content.buildings[b.def].name_key)), tr("hud.building.open.tooltip"))) {
                open_link(o.id, WindowList::Kind::Building, building);
            }
            y += link_h + ctx.s(3.0f);
        };
        if (home != nullptr) {
            link("home", "hud.villager.home", *home, v->home);
        }
        if (job != nullptr) {
            link("job", "hud.villager.job", *job, v->job);
        }
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

// A tree, a stone, a vein, a bush or herbs: what it is and what it gives.
void GameHud::node_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const std::uint32_t index = o.entity.index;
    if (!node_there(game, index)) {
        gone_window(ctx, s, o);
        return;
    }
    const sim::MapFeature& f = game.map().features[index];
    const sim::Node& n = game.nodes()[index];
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    const bool tree = f.type == sim::FeatureType::Tree;
    std::string name = tr(feature_key(f.type));
    std::vector<std::string> lines;
    if (tree) {
        if (f.species < content.flora.species.size()) {
            name = tr(content.flora.species[f.species].name_key);
        }
        lines.push_back(tr("hud.node.tree", static_cast<int>((sim::MapData::tree_height_cm(f) + 50) / 100)));
    }
    sim::DefIndex resource = sim::kNoDef;
    for (const sim::FeatureDef& d : content.features) {
        if (d.kind == f.type) {
            resource = d.resource;
            break;
        }
    }
    if (n.amount > 0 && resource < content.resources.size()) {
        lines.push_back(tr("hud.thing.gives", tr("hud.amount", tr(content.resources[resource].name_key), n.amount)));
    } else if (n.amount <= 0) {
        lines.push_back(tr("hud.node.empty"));
    }
    if (n.reserved != 0) {
        lines.push_back(tr("hud.node.busy"));
    }
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float button_h = std::round(ctx.s(34.0f));
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(pad + title_h + pad * 0.5f + button_h + pad * 0.5f + static_cast<float>(lines.size()) * line + pad)};
    bool open = true;
    if (!window(ctx, s, o.id, name, box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    float y = box.y + pad + title_h + pad * 0.5f;
    if (ctx.button(ctx.id("eye"), {box.x + pad, y, std::round((box.w - 2 * pad) * 0.5f), button_h}, tr("hud.window.eye"),
                   tr("hud.window.eye.tooltip"))) {
        services_.focus_camera(meters(f.x), meters(f.z));
    }
    y += button_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
}

// An animal, a soldier or a raider: what it is, what it is doing and, for
// game, what a hunter brings from one.
void GameHud::creature_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const sim::Creature* c = game.creatures().get(o.entity);
    if (c == nullptr) {
        gone_window(ctx, s, o);
        return;
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    std::string name = tr(creature_key(c->kind));
    std::vector<std::string> lines;
    switch (c->kind) {
        case sim::CreatureKind::Deer:
        case sim::CreatureKind::Boar: {
            std::string gives;
            const sim::DefIndex meat = content.find_resource("core:meat");
            const sim::DefIndex hide = content.find_resource("core:hide");
            if (meat != sim::kNoDef && game.hunt_meat() > 0) {
                gives = tr("hud.amount", tr(content.resources[meat].name_key), game.hunt_meat());
            }
            if (hide != sim::kNoDef && game.hunt_hides() > 0) {
                gives += (gives.empty() ? "" : ", ") + tr("hud.amount", tr(content.resources[hide].name_key), game.hunt_hides());
            }
            if (!gives.empty()) {
                lines.push_back(tr("hud.thing.gives", gives));
            }
            break;
        }
        case sim::CreatureKind::Wolf:
        case sim::CreatureKind::Bear: lines.push_back(tr("hud.creature.danger")); break;
        case sim::CreatureKind::Raider: lines.push_back(tr("hud.creature.raiderNote")); break;
        default:
            if (c->unit < content.units.size()) {
                name = tr(content.units[c->unit].name_key);
            }
            lines.push_back(tr("hud.creature.soldierOf", town_name(c->town)));
            break;
    }
    lines.push_back(tr("hud.villager.task", tr(creature_state_key(c->state))));
    lines.push_back(tr("hud.creature.health", c->health));
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float button_h = std::round(ctx.s(34.0f));
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(pad + title_h + pad * 0.5f + button_h + pad * 0.5f + static_cast<float>(lines.size()) * line + pad)};
    bool open = true;
    if (!window(ctx, s, o.id, name, box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    float y = box.y + pad + title_h + pad * 0.5f;
    if (ctx.button(ctx.id("eye"), {box.x + pad, y, std::round((box.w - 2 * pad) * 0.5f), button_h}, tr("hud.window.eye"),
                   tr("hud.window.eye.tooltip"))) {
        services_.focus_camera(meters(c->position.x), meters(c->position.z));
    }
    y += button_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
}

}  // namespace sc
