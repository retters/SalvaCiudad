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
        if (ctx.input().key(SDL_SCANCODE_ESCAPE)) {
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
    network_prompts(*s);
    // Phase 74: with no town yet there is nothing to build with.
    // Phase 79: nor for whoever watches.
    const bool has_town = game.founded(s->local_player()) && !s->spectating();
    if (has_town) {
        question(*s);
    }
    if (s->spectating()) {
        spectator(*s);
        if (s->seat() == GameSession::kNoSeat && ui.arrival_open) {
            arrival(*s);
        }
    } else if (!has_town || game.awaiting_founders()) {
        founding(ctx, *s);
    }
    join_requests(*s);
    rml_panels(ctx, *s);
    // Phase 123 to 125: every window is RmlUi's (rml_windows); here only the
    // closing of the fixed ones.
    for (const char* id : {"goods", "stats", "log", "layers", "trade", "army"}) {
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
    for (const std::string& id : closing_) {
        if (const WindowList::Object* o = windows_.object(id)) {
            // The selection goes with its window.
            const Selected sel = selected(ui);
            if (sel.valid && sel.kind == o->kind && sel.entity == o->entity) {
                ui.clear_selection();
            }
        }
        if (things_.rename_id == id) {
            things_.rename_id.clear();
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
                return tr(feature_name_key(f.type));
            }
            break;
        case WindowList::Kind::Walker: return tr("hud.walker.title");
        case WindowList::Kind::Creature:
            if (const sim::Creature* c = game.creatures().get(entity)) {
                return c->kind == sim::CreatureKind::Soldier && c->unit < content.units.size()
                           ? tr(content.units[c->unit].name_key)
                           : tr(creature_name_key(c->kind));
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

}  // namespace sc
