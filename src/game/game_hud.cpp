#include "game/game_hud.h"

#include "core/speed.h"

#include <algorithm>
#include <functional>
#include <cmath>

#include "i18n/translator.h"
#include "render/scene_renderer.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 52.0f;  // The RmlUi top bar (data/ui/hud/top.rcss) and its margin.
constexpr float kWindowW = 420.0f;  // Room for the title beside its three buttons, and for four in a row.

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
        case sim::PlaceError::Unreachable: return "hud.place.error.unreachable";
        case sim::PlaceError::DoorBelow: return "hud.place.error.doorBelow";
        case sim::PlaceError::Protected: return "hud.place.error.protected";
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

const char* supply_key(const sim::BuildingDef& def, const sim::Building& b) {
    if (b.supply == sim::Supply::Fine || b.stopped || b.state != sim::BuildingState::Complete) {
        return nullptr;
    }
    if (def.work == sim::WorkKind::Hunt) {
        return "hud.supply.noGame";
    }
    if (def.work == sim::WorkKind::Fish) {
        return "hud.supply.noFish";
    }
    return b.supply == sim::Supply::Exhausted   ? "hud.supply.exhausted"
           : b.supply == sim::Supply::OnlyFruit ? "hud.supply.onlyFruit"
           : b.supply == sim::Supply::Growing   ? "hud.supply.growing"
                                                : "hud.supply.waiting";
}

std::span<const WorkplaceOption> workplace_option_list() {
    static constexpr WorkplaceOption kOptions[] = {
        {sim::option::kFellFruit, 0, "hud.option.fellFruit.on", "hud.option.fellFruit.off", "hud.option.fellFruit.tooltip"},
        {sim::option::kReplant, 1, "hud.option.replant.on", "hud.option.replant.off", "hud.option.replant.tooltip"},
        {sim::option::kMatureOnly, 2, "hud.option.matureOnly.on", "hud.option.matureOnly.off", "hud.option.matureOnly.tooltip"},
    };
    return kOptions;
}

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
        case sim::Task::GoProvision: return "task.goProvision";
        case sim::Task::Scout: return "task.scout";
        case sim::Task::ScoutWait: return "task.scoutWait";
        case sim::Task::GoRest: return "task.goRest";
        case sim::Task::Rest: return "task.rest";
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

const char* place_error_text_key(sim::PlaceError e) {
    return place_error_key(e);
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
    if (ui.selected_walker != 0) {
        return {true, WindowList::Kind::Walker, sim::EntityId{ui.selected_walker - 1, 0}};
    }
    return {};
}

const char* feature_key(sim::FeatureType type) {
    switch (type) {
        case sim::FeatureType::Stone: return "feature.stone";
        case sim::FeatureType::StoneDeposit: return "feature.stoneDeposit";
        case sim::FeatureType::IronOre: return "feature.ironOre";
        case sim::FeatureType::BerryBush: return "feature.berryBush";
        case sim::FeatureType::Herbs: return "feature.herbs";
        case sim::FeatureType::BeeTree: return "feature.beeTree";
        case sim::FeatureType::Nest: return "feature.nest";
        case sim::FeatureType::Stump: return "feature.stump";
        case sim::FeatureType::MushroomRing: return "feature.mushroomRing";
        case sim::FeatureType::ClayDeposit: return "feature.clayDeposit";
        case sim::FeatureType::CoalDeposit: return "feature.coalDeposit";
        case sim::FeatureType::GoldDeposit: return "feature.goldDeposit";
        case sim::FeatureType::LooseStones: return "feature.looseStones";
        case sim::FeatureType::FishShoal: return "feature.fishShoal";
        case sim::FeatureType::ReedBank: return "feature.reedBank";
        case sim::FeatureType::Ducks: return "feature.ducks";
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
        // A building being placed, or the town center being founded.
        const bool choosing = choosing_site(game, ui, s->local_player()) && !ui.found_asked && ui.found_sent == 0;
        if (pressed(ctx, Action::GameRotateBuilding) && (ui.placing != sim::kNoDef || choosing)) {
            ui.rotation = static_cast<std::uint8_t>((ui.rotation + 1) & 3u);
        }
        if (ctx.input().key(SDL_SCANCODE_ESCAPE) && ctx.typing()) {
            rename_id_.clear();  // Esc while typing a name: only the typing ends.
        } else if (ctx.input().key(SDL_SCANCODE_ESCAPE)) {
            if (ui.found_asked) {
                ui.found_asked = false;  // The site again.
            } else if (ui.found_mode && ui.found_sent == 0) {
                ui.found_mode = false;   // A latecomer goes back to its arrival window.
            } else if (ui.field_farm.valid()) {
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
    rml_frame(ctx, *s);
    network_prompts(ctx, *s);
    // Phase 74: with no town yet there is nothing to build with.
    // Phase 79: nor for whoever watches.
    const bool has_town = game.founded(s->local_player()) && !s->spectating();
    if (has_town) {
        question(ctx, *s);
    }
    if (s->spectating()) {
        spectator(ctx, *s);
        if (s->seat() == GameSession::kNoSeat && ui.arrival_open) {
            arrival(ctx, *s);
        }
    } else if (!has_town || game.awaiting_founders()) {
        founding(ctx, *s);
    }
    join_requests(ctx, *s);

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
    // Phase 123: goods, statistics, events, layers and the camera windows
    // are RmlUi's (rml_windows); here only their closing.
    for (const char* id : {"goods", "stats", "log", "layers"}) {
        if (!*fixed_open(id) && windows_.open(id)) {
            windows_.close(id);
        }
    }
    for (int slot = 0; slot < kCameraWindows; ++slot) {
        const std::string id = "cam" + std::to_string(slot + 1);
        if (!ui.camera_windows[static_cast<std::size_t>(slot)].open && windows_.open(id)) {
            windows_.close(id);
        }
    }
    for (const WindowList::Object& o : windows_.objects()) {
        if (rml_object(o.kind)) {
            continue;  // Phase 124: in RmlUi (rml_windows).
        }
        jobs.push_back({o.id, [this, &ctx, s, o] {
                            switch (o.kind) {
                                case WindowList::Kind::Building: break;
                                case WindowList::Kind::Villager: villager_window(ctx, *s, o); break;
                                case WindowList::Kind::Node: node_window(ctx, *s, o); break;
                                case WindowList::Kind::Creature: creature_window(ctx, *s, o); break;
                                case WindowList::Kind::Walker: walker_window(ctx, *s, o); break;
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
        if (job == jobs.end() || (WindowList::is_object_id(id) && windows_.object(id) == nullptr) || windows_.hidden(id)) {
            continue;  // (Or it is behind another tab of its window.)
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
            case WindowList::Kind::Walker: ui.selected_walker = link.entity.index + 1; break;
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
            case WindowList::Kind::Walker: there = ui.walker_info && ui.walker_info(o->entity.index).there; break;
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

void GameHud::network_prompts(ui::Context& ctx, GameSession& s) {
    net::NetSession* net = services_.net();
    if (net == nullptr || !s.networked()) {
        return;
    }
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float bar_h = top_bar_bottom_;
    std::string waiting;
    for (const net::LobbyPlayer& p : net->lobby().players) {
        if (net->waiting_for() && *net->waiting_for() == p.slot && p.slot != net->local_slot()) {
            waiting = p.name;
        }
    }

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

// Phase 114: what a happening asks the town: the question and its two
// answers, under the top bar, for as long as it waits. Any seat of the town
// answers, and the answer is an order like any other.
void GameHud::question(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Happening* asked = nullptr;
    for (const sim::Happening& h : game.happenings()) {
        if (h.state == sim::HappeningState::Asked && h.town == s.town() && h.kind == sim::HappeningKind::Turtles) {
            asked = &h;
            break;
        }
    }
    if (asked == nullptr) {
        return;
    }
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const auto today = static_cast<std::uint32_t>(game.calendar_day());
    const int left = asked->until_day > today ? static_cast<int>(asked->until_day - today) : 0;
    const std::string q = tr("hud.ask.turtles", static_cast<int>(asked->count));
    const std::string days = tr("hud.ask.days", left);
    const float pad = ctx.s(12.0f);
    const float bh = std::round(ctx.s(36.0f));
    const float line = ctx.text().line_height(st);
    const float line2 = ctx.text().line_height(small);
    const float see_w = ctx.text().measure(st, tr("hud.ask.see")) + 2 * pad;
    const float width = std::min(ctx.width() - 2 * pad,
                                 std::max({ctx.s(460.0f), ctx.text().measure(st, q) + 3 * pad + see_w, ctx.text().measure(small, days) + 2 * pad}));
    const float bar_h = std::round(ctx.s(44.0f));
    const ui::Rect box{std::round((ctx.width() - width) * 0.5f), std::round(bar_h + ctx.s(10.0f)), std::round(width),
                       std::round(line + line2 + bh + 3.5f * pad)};
    ctx.panel(box);
    block(s, box);
    ctx.label({box.x + pad, box.y + pad, box.w - 3 * pad - see_w, line}, q, st, ctx.theme().text);
    if (ctx.button(ctx.id("ask_see"), {box.right() - pad - see_w, box.y + pad - ctx.s(4.0f), see_w, line + ctx.s(8.0f)}, tr("hud.ask.see"))) {
        services_.focus_camera(meters(asked->at.x), meters(asked->at.z));
    }
    ctx.label({box.x + pad, box.y + pad + line + ctx.s(4.0f), box.w - 2 * pad, line2}, days, small, ctx.theme().text_dim);
    const auto answer = [&](std::int32_t which) {
        sim::Command c;
        c.type = sim::CommandType::AnswerHappening;
        c.def = static_cast<std::uint16_t>(asked->kind);
        c.value = which;
        s.issue(c);
    };
    const float bw = (box.w - 3 * pad) * 0.5f;
    const float by = box.bottom() - pad - bh;
    if (ctx.button(ctx.id("ask_first"), {box.x + pad, by, bw, bh}, tr("hud.ask.turtles.keep"),
                   tr("hud.ask.turtles.keep.tooltip", static_cast<int>(sim::village::kProtectDays)))) {
        answer(1);
    } else if (ctx.button(ctx.id("ask_second"), {box.x + 2 * pad + bw, by, bw, bh}, tr("hud.ask.turtles.take"),
                          tr("hud.ask.turtles.take.tooltip", static_cast<int>(asked->count) * sim::village::kTurtleEggs))) {
        answer(2);
    }
}

std::string GameHud::placement_text(GameSession& s, bool& bad) const {
    const GameSession::Interaction& ui = s.ui();
    const KeyBindings& b = services_.settings().input.bindings;
    std::string text = ui.field_farm.valid() ? tr("hud.place.field.hint")
                                             : tr("hud.place.hint", key_display_name(b.key(Action::GameRotateBuilding, 0)));
    // Phase 110: a fisher's hut being placed says what it would have within reach there.
    if (const sim::Content& c = s.game().content();
        !ui.field_farm.valid() && ui.hover_valid && ui.placing < c.buildings.size() && c.buildings[ui.placing].work == sim::WorkKind::Fish) {
        const sim::BuildingDef& hut = c.buildings[ui.placing];
        const sim::Game::FishSpots spots =
            s.game().fish_spots(ui.hover_x + hut.width / 2, ui.hover_z + hut.depth / 2, hut.work_radius);
        text += "  ·  " + tr("hud.place.fisher", spots.shoals + spots.reeds);
    }
    // Phase 112: a woodcutter being placed where it would fell the trees of a unicorn's glade.
    if (!ui.field_farm.valid() && ui.hover_valid && s.game().fells_by_unicorn(ui.placing, ui.hover_x, ui.hover_z)) {
        text += "  ·  " + tr("hud.place.unicorn");
    }
    // Phase 93: a line being traced says how long it is and what it will cost.
    const sim::Content& content = s.game().content();
    const bool tracing = ui.placing < content.buildings.size() && !content.buildings[ui.placing].line.empty() &&
                         !content.buildings[ui.placing].gate && ui.trace_modules > 0;
    if (tracing) {
        text = tr("hud.place.trace.hint");
        if (ui.line_dragging) {
            std::string cost;
            for (const sim::ResourceAmount& c : content.buildings[ui.placing].cost) {
                if (c.resource < content.resources.size()) {
                    cost += (cost.empty() ? "" : ", ") + std::to_string(c.amount * ui.trace_fit) + " " +
                            tr(content.resources[c.resource].name_key);
                }
            }
            text = tr("hud.place.trace.count", ui.trace_modules, ui.trace_fit, cost.empty() ? tr("hud.place.trace.free") : cost);
        }
    }
    bad = false;
    if (ui.hover_valid && ui.hover_error != sim::PlaceError::None) {
        text = tr(place_error_key(ui.hover_error));
        bad = true;
    }
    return text;
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
        if (!game.town_exists(p)) {
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
    // The name the seat has in the game (phase 75), then the lobby's.
    if (GameSession* s = services_.session()) {
        if (player < s->game().player_count() && !s->game().player(player).name.empty()) {
            return s->game().player(player).name;
        }
    }
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
        if (game.town_exists(p) && p != town) {
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

std::vector<ui::Rect> GameHud::button_row(ui::Context& ctx, const ui::Rect& box, float y, float h,
                                          const std::vector<std::string>& labels) const {
    // Each as wide as its text asks, stretched (or squeezed) to fill the row.
    const float pad = ctx.s(14.0f);
    const float gap = ctx.s(6.0f);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    std::vector<float> want;
    float total = 0.0f;
    for (const std::string& l : labels) {
        want.push_back(ctx.text().measure(st, l) + ctx.s(22.0f));
        total += want.back();
    }
    const float room = box.w - 2 * pad - gap * static_cast<float>(labels.empty() ? 0 : labels.size() - 1);
    std::vector<ui::Rect> out;
    float x = box.x + pad;
    for (std::size_t i = 0; i < labels.size(); ++i) {
        const float w = i + 1 == labels.size() ? box.right() - pad - x : std::round(want[i] * room / std::max(1.0f, total));
        out.push_back({x, y, w, h});
        x += w + gap;
    }
    return out;
}

std::string GameHud::thing_title(const sim::Game& game, WindowList::Kind kind, sim::EntityId entity) const {
    const sim::Content& content = game.content();
    switch (kind) {
        case WindowList::Kind::Building:
            if (const sim::Building* b = game.buildings().get(entity)) {
                return tr(content.buildings[b->def].name_key);
            }
            break;
        case WindowList::Kind::Villager:
            if (const sim::Villager* v = game.villagers().get(entity)) {
                const std::string name = game.villager_name(*v);
                return name.empty() ? tr(v->sex == sim::Sex::Female ? "hud.villager.woman" : "hud.villager.man") : name;
            }
            break;
        case WindowList::Kind::Node:
            if (entity.index < game.map().features.size()) {
                const sim::MapFeature& f = game.map().features[entity.index];
                if (f.type == sim::FeatureType::Tree && f.species < content.flora.species.size()) {
                    return tr(content.flora.species[f.species].name_key);
                }
                return tr(feature_key(f.type));
            }
            break;
        case WindowList::Kind::Walker: return tr("hud.walker.title");
        case WindowList::Kind::Creature:
            if (const sim::Creature* c = game.creatures().get(entity)) {
                return c->kind == sim::CreatureKind::Soldier && c->unit < content.units.size()
                           ? tr(content.units[c->unit].name_key)
                           : tr(creature_key(c->kind));
            }
            break;
    }
    return tr("hud.window.gone.title");
}

void GameHud::open_camera(GameSession& s, WindowList::Kind kind, sim::EntityId entity) {
    auto& windows = s.ui().camera_windows;
    int slot = -1;
    for (int i = 0; i < kCameraWindows; ++i) {
        const auto& w = windows[static_cast<std::size_t>(i)];
        if (w.open && w.kind == static_cast<std::uint8_t>(kind) && w.entity == entity) {
            windows_.raise("cam" + std::to_string(i + 1));  // It has one already.
            return;
        }
    }
    for (int i = 0; i < kCameraWindows && slot < 0; ++i) {
        slot = windows[static_cast<std::size_t>(i)].open ? -1 : i;
    }
    if (slot < 0) {
        // Both taken: the one opened first looks at this now.
        slot = camera_opened_[0] <= camera_opened_[1] ? 0 : 1;
    }
    GameSession::Interaction::CameraWindow& w = windows[static_cast<std::size_t>(slot)];
    w = {};
    w.open = true;
    w.kind = static_cast<std::uint8_t>(kind);
    w.entity = entity;
    w.distance = kind == WindowList::Kind::Building ? 30.0f : kind == WindowList::Kind::Node ? 20.0f : 9.0f;
    camera_opened_[slot] = ++camera_count_;
    windows_.raise("cam" + std::to_string(slot + 1));
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
    lines.push_back(tr("hud.villager.task", tr(v->order == sim::Order::Returning ? "task.scoutBack" : task_text_key(v->task))));
    if (job == nullptr) {
        lines.push_back(tr(game.adult(*v) ? "hud.villager.laborer" : "hud.villager.child"));
    } else if (const char* key = supply_key(content.buildings[job->def], *job)) {
        lines.push_back(tr(key));
    }
    // Phase 66: an explorer goes where a right click sends it.
    if (job != nullptr && mine && content.buildings[job->def].work == sim::WorkKind::Explore) {
        lines.push_back(tr("hud.explorer.provisions", v->provisions * 100 / sim::village::kProvisions));
        lines.push_back(tr("hud.explorer.hint"));
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
    // Food, warmth and health; energy if the game has it; a line when in the dark.
    const float bar_block = static_cast<float>(game.rules().rest ? 4 : 3) * (line + ctx.s(10.0f)) +
                            (game.in_the_dark(*v) ? line : 0.0f);
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
        const bool followed = ui.followed_villager == o.entity;
        const std::vector<std::string> labels = {tr("hud.window.eye"), tr("hud.window.camera"),
                                                 tr(followed ? "hud.villager.unfollow" : "hud.villager.follow"),
                                                 tr("hud.villager.rename")};
        const std::vector<ui::Rect> row = button_row(ctx, box, y, button_h, labels);
        if (ctx.button(ctx.id("eye"), row[0], labels[0], tr("hud.window.eye.tooltip"))) {
            services_.focus_camera(meters(v->position.x), meters(v->position.z));
        }
        if (ctx.button(ctx.id("camera"), row[1], labels[1], tr("hud.window.camera.tooltip"))) {
            open_camera(s, WindowList::Kind::Villager, o.entity);
        }
        if (ctx.button(ctx.id("follow"), row[2], labels[2], tr("hud.villager.follow.tooltip"), true, followed)) {
            ui.followed_villager = followed ? sim::EntityId{} : o.entity;
        }
        if (ctx.button(ctx.id("rename"), row[3], labels[3], tr("hud.villager.rename.tooltip"), mine, renaming)) {
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
    if (game.rules().rest) {
        bar(tr("hud.villager.energy"), static_cast<float>(v->energy) / static_cast<float>(sim::village::kEnergyMax),
            ui::Color::rgb(0x7FB0E0));
    }
    if (game.in_the_dark(*v)) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.villager.dark", sim::village::kDarkPercent), body,
                  ui::Color::rgb(0x9CC7F0));
        y += line;
    }
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
        // Phase 84: a fruit tree says what hangs from it.
        if (f.species < content.flora.species.size() && content.flora.species[f.species].fruit_tree() && n.amount > 0) {
            const std::int32_t fruit = game.fruit_on(index);
            lines.push_back(fruit > 0 ? tr("hud.node.fruit", fruit)
                            : content.flora.species[f.species].fruit[f.size] > 0 ? tr("hud.node.noFruit")
                                                                                   : tr("hud.node.youngFruit"));
        }
    }
    sim::DefIndex resource = sim::kNoDef;
    const sim::FeatureDef* feature = nullptr;
    for (const sim::FeatureDef& d : content.features) {
        if (d.kind == f.type) {
            resource = d.resource;
            feature = &d;
            break;
        }
    }
    if (feature != nullptr && feature->seasons != 0 && n.amount > 0 && resource < content.resources.size()) {
        // Phase 98: what it has now, and when it gives.
        static constexpr const char* kSeasons[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                   "hud.season.winter"};
        const std::string what = tr(content.resources[resource].name_key);
        const std::int32_t has = game.fruit_on(index);
        lines.push_back(has > 0 ? tr("feature.yield.now", what, has) : tr("feature.yield.empty"));
        std::string when;
        for (std::size_t season = 0; season < 4; ++season) {
            if (((feature->seasons >> season) & 1u) != 0) {
                when += (when.empty() ? "" : ", ") + tr(kSeasons[season]);
            }
        }
        lines.push_back(tr(!feature->after_rain     ? "feature.yield.season"
                           : game.rules().rain != 0 ? "feature.yield.afterRain"
                                                    : "feature.yield.dry",
                           what, when));
    } else if (n.amount > 0 && resource < content.resources.size()) {
        lines.push_back(tr("hud.thing.gives", tr("hud.amount", tr(content.resources[resource].name_key), n.amount)));
    } else if (n.amount <= 0) {
        lines.push_back(tr(tree ? "hud.node.sprout" : "hud.node.empty"));
    }
    if (tree && n.amount > 0 && n.grow_day != sim::kNeverGrows) {
        lines.push_back(tr("hud.node.growing"));
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
    {
        const std::vector<std::string> labels = {tr("hud.window.eye"), tr("hud.window.camera")};
        const std::vector<ui::Rect> row = button_row(ctx, box, y, button_h, labels);
        if (ctx.button(ctx.id("eye"), row[0], labels[0], tr("hud.window.eye.tooltip"))) {
            services_.focus_camera(meters(f.x), meters(f.z));
        }
        if (ctx.button(ctx.id("camera"), row[1], labels[1], tr("hud.window.camera.tooltip"))) {
            open_camera(s, WindowList::Kind::Node, o.entity);
        }
    }
    y += button_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
}

// One of the people placed with the developer tools: not a villager of the
// game, so only what it is and where.
void GameHud::walker_window(ui::Context& ctx, GameSession& s, const WindowList::Object& o) {
    GameSession::Interaction& ui = s.ui();
    const GameSession::Interaction::WalkerInfo info =
        ui.walker_info ? ui.walker_info(o.entity.index) : GameSession::Interaction::WalkerInfo{};
    if (!info.there) {
        gone_window(ctx, s, o);
        return;
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float w = std::min(ctx.s(kWindowW), ctx.width() - 2 * pad);
    const std::vector<std::string> lines = {tr("hud.walker.note"), tr("hud.walker.model", info.model)};
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float button_h = std::round(ctx.s(34.0f));
    ui::Rect box{std::round(ctx.width() - w - pad), std::round(std::max(ctx.s(kTopBarH) + pad, right_top_)), std::round(w),
                 std::round(pad + title_h + pad * 0.5f + button_h + pad * 0.5f + static_cast<float>(lines.size()) * line + pad)};
    bool open = true;
    if (!window(ctx, s, o.id, tr("hud.walker.title"), box, open)) {
        if (!open) {
            closing_.push_back(o.id);
        }
        return;
    }
    float y = box.y + pad + title_h + pad * 0.5f;
    const bool followed = ui.followed_walker == o.entity.index + 1;
    const std::vector<std::string> labels = {tr("hud.window.eye"), tr("hud.window.camera"),
                                             tr(followed ? "hud.villager.unfollow" : "hud.villager.follow")};
    const std::vector<ui::Rect> row = button_row(ctx, box, y, button_h, labels);
    if (ctx.button(ctx.id("eye"), row[0], labels[0], tr("hud.window.eye.tooltip"))) {
        services_.focus_camera(info.x, info.z);
    }
    if (ctx.button(ctx.id("camera"), row[1], labels[1], tr("hud.window.camera.tooltip"))) {
        open_camera(s, WindowList::Kind::Walker, o.entity);
    }
    if (ctx.button(ctx.id("follow"), row[2], labels[2], tr("hud.villager.follow.tooltip"), true, followed)) {
        ui.followed_walker = followed ? 0u : o.entity.index + 1;
        ui.followed_villager = {};
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
    {
        const std::vector<std::string> labels = {tr("hud.window.eye"), tr("hud.window.camera")};
        const std::vector<ui::Rect> row = button_row(ctx, box, y, button_h, labels);
        if (ctx.button(ctx.id("eye"), row[0], labels[0], tr("hud.window.eye.tooltip"))) {
            services_.focus_camera(meters(c->position.x), meters(c->position.z));
        }
        if (ctx.button(ctx.id("camera"), row[1], labels[1], tr("hud.window.camera.tooltip"))) {
            open_camera(s, WindowList::Kind::Creature, o.entity);
        }
    }
    y += button_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
}

}  // namespace sc
