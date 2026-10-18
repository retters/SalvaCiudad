// The game windows in RmlUi (phase 123): the frame of every window (the
// hud/window.rml template: icon, title, square buttons, tabs, the resize
// corner) moved and stacked as WindowList says, and the first windows that
// live in it: goods, statistics, events, layers and the camera windows.
// WindowList stays the model (places, depth, groups, tabs, pins); the drag,
// the magnets, docking and stacking work as in hud_windows.cpp, from
// RmlUi's drag events. Phase 124: the windows of buildings, whose rows come
// from thing_rows.cpp (hud/win/thing.rml). The other windows still use the
// old frame until they move (phase 125).
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <format>

#include <RmlUi/Core/Context.h>
#include <RmlUi/Core/DataModelHandle.h>
#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Event.h>

#include "game/game_hud.h"
#include "i18n/translator.h"
#include "render/scene_renderer.h"
#include "ui/rml/rml_ui.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 52.0f;   // As in game_hud.cpp.
constexpr float kMinW = 280.0f;     // Design units.
constexpr float kSnap = 12.0f;
constexpr float kTabH = 30.0f;
constexpr float kThingW = 420.0f;   // The windows of things, as the old ones.

struct FixedWindow {
    const char* id;
    const char* doc;
    const char* icon;
    float width;
};
constexpr FixedWindow kFixed[] = {
    {"goods", "hud/win/goods.rml", "icon-box", 440.0f},
    {"stats", "hud/win/stats.rml", "icon-chart", 380.0f},
    {"log", "hud/win/log.rml", "icon-list", 460.0f},
    {"layers", "hud/win/layers.rml", "icon-layers", 300.0f},
    {"trade", "hud/win/thing.rml#trade", "icon-scales", 440.0f},  // Phase 125.
    {"army", "hud/win/thing.rml#army", "icon-swords", 420.0f},
};

bool inside(const ui::Rect& r, float x, float y) {
    return x >= r.x && y >= r.y && x < r.right() && y < r.bottom();
}

// The nearest element from `e` up whose id is one of the frame's parts, or
// that is a tab; null if none (the click was on the content).
Rml::Element* frame_part(Rml::Element* e) {
    for (; e != nullptr; e = e->GetParentNode()) {
        const Rml::String& id = e->GetId();
        if (id == "close" || id == "pin" || id == "minimize" || id == "view" || id == "camera" || id == "bar" ||
            id == "grip" || id == "picture" || e->HasAttribute("data-tab")) {
            return e;
        }
        if (e->GetOwnerDocument() == e) {
            break;
        }
    }
    return nullptr;
}

// A slider's value, as its element has it (a range input keeps it in its
// "value" attribute).
int control_value(Rml::Element* e) {
    return e != nullptr ? static_cast<int>(std::lround(std::strtod(e->GetAttribute<Rml::String>("value", "0").c_str(), nullptr)))
                        : 0;
}

}  // namespace

bool GameHud::rml_object(WindowList::Kind) {
    return true;  // Phase 125: all of them.
}

void GameHud::rows_into(Rml::Element* box, const ThingRows& view, std::vector<std::string>& shown) {
    if (box == nullptr) {
        return;
    }
    std::vector<std::string> keys;
    keys.reserve(view.rows.size());
    for (const WinRow& r : view.rows) {
        keys.push_back(row_key(r));
    }
    if (keys.size() != shown.size() || box->GetNumChildren() != static_cast<int>(keys.size())) {
        // Other rows: all again.
        std::string all;
        for (const WinRow& r : view.rows) {
            all += "<div class=\"r\">" + row_rml(r) + "</div>";
        }
        box->SetInnerRML(all);
    } else {
        // The same rows: only those that changed, so a button under the
        // pointer stays the same element while the rest moves on.
        for (std::size_t i = 0; i < keys.size(); ++i) {
            Rml::Element* row = box->GetChild(static_cast<int>(i));
            if (keys[i] != shown[i]) {
                row->SetInnerRML(row_rml(view.rows[i]));
            } else if (Rml::Element* input = row->GetFirstChild(); input != nullptr && view.rows[i].kind == WinRow::Kind::Slider &&
                                                                   control_value(input) != view.rows[i].value) {
                input->SetAttribute("value", std::to_string(view.rows[i].value));
            }
        }
    }
    shown = std::move(keys);
}

void GameHud::rml_rows(Rml::ElementDocument& doc, RmlWindow& w) {
    rows_into(doc.GetElementById("rows"), w.view, w.row_keys);
}

void GameHud::rml_act(GameSession& s, const std::string& id, int act, const RowInput& input) {
    const auto found = rml_windows_.find(id);
    if (found == rml_windows_.end() || act < 0 || static_cast<std::size_t>(act) >= found->second.view.acts.size()) {
        return;
    }
    const RowFn fn = found->second.view.acts[static_cast<std::size_t>(act)];  // A copy: it may change what holds it.
    RowEffects effects;
    fn(s, input, effects);
    if (effects.close) {
        closing_.push_back(id);
    }
    if (effects.link) {
        open_link(id, effects.kind, effects.entity);
    }
    if (effects.focus) {
        services_.focus_camera(effects.x, effects.z);
    }
}

std::string GameHud::rml_window_doc(const std::string& id) const {
    for (const FixedWindow& f : kFixed) {
        if (id == f.id) {
            return f.doc;
        }
    }
    if (WindowList::is_camera_id(id) && id.size() == 4) {
        return std::string("hud/win/camera.rml#") + id[3];
    }
    if (WindowList::is_object_id(id)) {
        return "hud/win/thing.rml#" + id;
    }
    return {};
}

bool* GameHud::fixed_open(const std::string& id) {
    return id == "goods"    ? &goods_open_
           : id == "stats"  ? &stats_open_
           : id == "log"    ? &log_open_
           : id == "layers" ? &layers_open_
           : id == "trade"  ? &trade_open_
           : id == "army"   ? &army_open_
                            : nullptr;
}

void GameHud::rml_window_models(rml::RmlUi& rml) {
    Rml::Context& c = *rml.context();
    if (Rml::DataModelConstructor m = c.CreateDataModel("goods")) {
        if (auto item = m.RegisterStruct<HudItem>()) {
            item.RegisterMember("text", &HudItem::text);
            item.RegisterMember("image", &HudItem::image);
            item.RegisterMember("sprite", &HudItem::sprite);
            item.RegisterMember("tip", &HudItem::tip);
        }
        m.RegisterArray<std::vector<HudItem>>();
        if (auto cat = m.RegisterStruct<GoodsCat>()) {
            cat.RegisterMember("name", &GoodsCat::name);
            cat.RegisterMember("goods", &GoodsCat::goods);
        }
        m.RegisterArray<std::vector<GoodsCat>>();
        m.Bind("cats", &goods_cats_);
        goods_model_ = m.GetModelHandle();
    }
    if (Rml::DataModelConstructor m = c.CreateDataModel("stats")) {
        m.RegisterArray<std::vector<std::string>>();
        m.Bind("lines", &stats_lines_);
        stats_model_ = m.GetModelHandle();
    }
    if (Rml::DataModelConstructor m = c.CreateDataModel("log")) {
        if (auto n = m.RegisterStruct<HudNote>()) {
            n.RegisterMember("text", &HudNote::text);
            n.RegisterMember("tip", &HudNote::tip);
            n.RegisterMember("has_pos", &HudNote::has_pos);
        }
        m.RegisterArray<std::vector<HudNote>>();
        m.Bind("rows", &log_rows_);
        m.BindEventCallback("go", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            const int i = args.empty() ? -1 : args[0].Get<int>(-1);
            if (i >= 0 && static_cast<std::size_t>(i) < log_index_.size()) {
                const Note& n = notes_[log_index_[static_cast<std::size_t>(i)]];
                if (n.has_pos) {
                    services_.focus_camera(n.x, n.z);
                }
            }
        });
        log_model_ = m.GetModelHandle();
    }
    if (Rml::DataModelConstructor m = c.CreateDataModel("layers")) {
        if (auto l = m.RegisterStruct<LayerRow>()) {
            l.RegisterMember("name", &LayerRow::name);
            l.RegisterMember("tip", &LayerRow::tip);
            l.RegisterMember("on", &LayerRow::on);
        }
        m.RegisterArray<std::vector<LayerRow>>();
        m.Bind("rows", &layer_rows_);
        m.BindEventCallback("pick", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            if (!args.empty()) {
                services_.set_overlay(args[0].Get<int>(0));
            }
        });
        layers_model_ = m.GetModelHandle();
    }
}

void GameHud::rml_window_contents(GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    // Goods: what the town has, by category.
    if (goods_open_) {
        static constexpr const char* kCats[] = {"hud.goods.food", "hud.goods.material", "hud.goods.fuel", "hud.goods.good"};
        const std::vector<std::int32_t> stored = game.stored(s.town());
        std::vector<GoodsCat> cats;
        for (std::size_t c = 0; c < std::size(kCats); ++c) {
            GoodsCat cat;
            cat.name = tr(kCats[c]);
            for (std::size_t r = 0; r < stored.size(); ++r) {
                const sim::ResourceDef& d = content.resources[r];
                if (static_cast<std::size_t>(d.category) != c || stored[r] <= 0) {
                    continue;
                }
                HudItem item;
                item.text = tr("hud.amount", tr(d.name_key), stored[r]);
                item.tip = tr(d.name_key) + "\n" + tr("hud.goods.value", d.value);
                if (d.nutrition > 0) {
                    item.tip += "\n" + tr("hud.goods.nutrition", d.nutrition);
                }
                good_image(d, !d.pile.empty(), item);
                cat.goods.push_back(std::move(item));
            }
            if (!cat.goods.empty()) {
                cats.push_back(std::move(cat));
            }
        }
        if (!(cats == goods_cats_)) {
            goods_cats_ = std::move(cats);
            goods_model_.DirtyAllVariables();
        }
    }
    // Statistics.
    if (stats_open_) {
        const std::uint8_t town = s.town();
        const sim::PlayerState& ps = game.player(town);
        const std::int32_t pop = game.population(town);
        const std::int32_t adults = game.population(town, true);
        std::string peoples;
        std::vector<std::int32_t> per_race(content.races.size(), 0);
        for (const sim::Villager& v : game.villagers().data()) {
            if (v.owner == town && v.race < per_race.size()) {
                ++per_race[v.race];
            }
        }
        for (std::size_t r = 0; r < content.races.size(); ++r) {
            if (per_race[r] > 0) {
                peoples += (peoples.empty() ? "" : ", ") + tr("hud.amount", tr(content.races[r].name_key), per_race[r]);
            }
        }
        std::vector<std::string> lines = {
            tr("hud.stats.population", pop, adults, pop - adults),
            tr("hud.stats.births", ps.births, ps.arrivals),
            tr("hud.stats.deaths", ps.deaths, ps.departures),
            tr("hud.stats.happiness", game.happiness(town)),
            tr("hud.stats.sick", game.sick(town)),
            tr("hud.stats.burned", ps.burned_down),
            tr("hud.stats.raids", ps.raids),
            tr("hud.stats.army", game.soldiers(town), game.military_power(town)),
            tr("hud.stats.gold", game.gold(town)),
            tr("hud.stats.score", game.score(town)),
            tr("hud.stats.level", game.tier(town)),
        };
        if (!peoples.empty()) {
            lines.push_back(tr("hud.stats.races", peoples));
        }
        if (lines != stats_lines_) {
            stats_lines_ = std::move(lines);
            stats_model_.DirtyAllVariables();
        }
    }
    // Events: the last twenty, newest first.
    if (log_open_) {
        std::vector<HudNote> rows;
        std::vector<std::size_t> index;
        for (std::size_t k = 0; k < std::min<std::size_t>(notes_.size(), 20); ++k) {
            const std::size_t at = notes_.size() - 1 - k;
            const Note& n = notes_[at];
            HudNote row;
            row.text = tr("hud.log.row", n.year, n.month, n.day,
                          n.count > 1 ? n.text + " (×" + std::to_string(n.count) + ")" : n.text);
            row.has_pos = n.has_pos;
            row.tip = n.has_pos ? tr("hud.log.goTo") : std::string();
            rows.push_back(std::move(row));
            index.push_back(at);
        }
        log_index_ = std::move(index);
        if (!(rows == log_rows_)) {
            log_rows_ = std::move(rows);
            log_model_.DirtyAllVariables();
        }
    }
    // Layers.
    if (layers_open_) {
        static constexpr const char* kLayers[] = {"hud.layers.none",   "hud.layers.fertility", "hud.layers.beauty",
                                                  "hud.layers.water",  "hud.layers.market",    "hud.layers.religion",
                                                  "hud.layers.health", "hud.layers.fire",      "hud.layers.routes"};
        std::vector<LayerRow> rows;
        for (std::size_t i = 0; i < std::size(kLayers); ++i) {
            rows.push_back({tr(kLayers[i]), tr(std::string(kLayers[i]) + ".tooltip"),
                            services_.overlay() == static_cast<int>(i)});
        }
        if (!(rows == layer_rows_)) {
            layer_rows_ = std::move(rows);
            layers_model_.DirtyAllVariables();
        }
    }
}

void GameHud::rml_windows(ui::Context& ctx, GameSession& s, rml::RmlUi& rml) {
    const float sc = ctx.s(1.0f);
    rml_scale_ = sc;
    rml_width_ = ctx.width();
    rml_height_ = ctx.height();
    const float top = std::round(ctx.s(kTopBarH));
    rml_window_contents(s);

    // Which windows are open now: the fixed ones by their flags, the camera
    // windows by the game's list.
    std::vector<std::string> open;
    for (const FixedWindow& f : kFixed) {
        if (*fixed_open(f.id)) {
            open.emplace_back(f.id);
        }
    }
    for (int slot = 0; slot < kCameraWindows; ++slot) {
        if (s.ui().camera_windows[static_cast<std::size_t>(slot)].open) {
            open.push_back("cam" + std::to_string(slot + 1));
        }
    }
    for (const WindowList::Object& o : windows_.objects()) {
        if (rml_object(o.kind)) {
            open.push_back(o.id);
        }
    }
    for (const std::string& id : open) {
        if (!windows_.open(id)) {
            windows_.raise(id);  // Opened without a click: in front.
        }
    }
    // The documents of windows that closed go away.
    for (auto it = rml_windows_.begin(); it != rml_windows_.end();) {
        if (std::find(open.begin(), open.end(), it->first) == open.end()) {
            (void)rml.show_document(it->second.doc, false);
            it = rml_windows_.erase(it);
        } else {
            ++it;
        }
    }

    for (const std::string& id : windows_.order()) {
        if (std::find(open.begin(), open.end(), id) == open.end()) {
            continue;
        }
        RmlWindow& w = rml_windows_[id];
        w.doc = rml_window_doc(id);
        // Behind another tab of its stack: not drawn.
        if (windows_.hidden(id)) {
            (void)rml.show_document(w.doc, false);
            continue;
        }
        if (!rml.document_shown(w.doc)) {
            (void)rml.show_document(w.doc, true);
        }
        Rml::ElementDocument* doc = rml.document(w.doc);
        if (doc == nullptr) {
            continue;
        }
        const WindowList::Object* obj = windows_.object(id);
        if (doc != w.attached) {
            // A new document (or reloaded with the language or the style).
            w.attached = doc;
            w.tabs.clear();
            w.title.clear();
            w.icon.clear();
            w.row_keys.clear();
            for (const char* type : {"mousedown", "click", "change", "dragstart", "drag", "dragend", "mousescroll"}) {
                doc->AddEventListener(type, this);
            }
            const bool camera = WindowList::is_camera_id(id);
            doc->SetClass("no-view", obj == nullptr);  // Ver and Cámara are for the windows of things.
            if (Rml::Element* icon = doc->GetElementById("icon"); icon != nullptr && obj == nullptr) {
                for (const FixedWindow& f : kFixed) {
                    if (id == f.id) {
                        icon->SetAttribute("sprite", f.icon);
                    }
                }
                if (camera) {
                    icon->SetAttribute("sprite", "icon-camera");
                }
                icon->SetClass("sprite", true);
            }
            if (camera) {
                if (Rml::Element* pic = doc->GetElementById("picture")) {
                    pic->SetAttribute("src", std::string("/ext/") + id);
                }
            }
        }
        // Phase 124: a thing's rows and its picture; phase 125: trade and army.
        if (id == "trade" || id == "army") {
            w.view = id == "trade" ? trade_rows(s, things_, town_names()) : army_rows(s, things_, town_names());
            if (w.view.rows.empty()) {
                trade_open_ = false;  // Nobody to trade with any more: it closes with the next frame.
            }
            rml_rows(*doc, w);
        }
        if (obj != nullptr) {
            w.view = thing_rows(s, id, obj->kind, obj->entity, things_, town_names());
            if (!w.view.icon.empty() && w.view.icon != w.icon) {
                w.icon = w.view.icon;
                if (Rml::Element* icon = doc->GetElementById("icon")) {
                    if (w.view.icon_sprite) {
                        icon->RemoveAttribute("src");
                        icon->SetAttribute("sprite", w.icon);
                    } else {
                        icon->RemoveAttribute("sprite");
                        icon->SetAttribute("src", w.icon);
                    }
                    icon->SetClass("sprite", w.view.icon_sprite);
                }
            }
            rml_rows(*doc, w);
        }
        WindowList::Place& p = windows_.place(id);
        // Title and pin.
        const std::string title = obj != nullptr && w.view.gone ? tr("hud.window.gone.title") : window_title(s, id);
        if (title != w.title) {
            w.title = title;
            if (Rml::Element* t = doc->GetElementById("title")) {
                t->SetInnerRML(rml_escape(title));
            }
        }
        doc->SetClass("minimized", p.minimized);
        if (Rml::Element* pin = doc->GetElementById("pin")) {
            pin->SetClass("on", p.pinned);
            pin->SetAttribute("tip", p.pinned ? "@hud.window.pinned" : "@hud.window.pin.tooltip");
        }
        if (Rml::Element* m = doc->GetElementById("minimize")) {
            m->SetAttribute("tip", p.minimized ? "@hud.window.restore.tooltip" : "@hud.window.minimize.tooltip");
        }
        // The tabs of its stack.
        const std::vector<std::string> tabs = windows_.tabs(id);
        std::string tab_rml;
        for (const std::string& t : tabs) {
            tab_rml += std::format("<div class=\"tab{}\" data-tab=\"{}\">{}</div>", t == id ? " on" : "", rml_escape(t),
                                   rml_escape(window_title(s, t)));
        }
        if (tab_rml != w.tabs) {
            w.tabs = tab_rml;
            if (Rml::Element* strip = doc->GetElementById("tabs")) {
                strip->SetInnerRML(tab_rml);
            }
        }
        const float tab_h = tabs.empty() ? 0.0f : std::round(ctx.s(kTabH));

        // Where it goes: as the player left it, or at its first place.
        float width = 0.0f;
        for (const FixedWindow& f : kFixed) {
            if (id == f.id) {
                width = f.width;
            }
        }
        if (WindowList::is_camera_id(id)) {
            width = static_cast<float>(render::kInsetWidth) + 30.0f;
        }
        if (obj != nullptr) {
            width = kThingW;
        }
        const float first_w = std::round(std::min(ctx.s(width), ctx.width() - ctx.s(28.0f)));
        // The windows of things start on the right, below the minimap, as before.
        ui::Rect box{obj != nullptr ? std::round(ctx.width() - first_w - ctx.s(14.0f)) : left_x(ctx),
                     std::round(obj != nullptr ? std::max(top + ctx.s(14.0f), right_top_) : top + ctx.s(14.0f)), first_w,
                     0.0f};
        if (p.w > 0.0f) {
            box.w = std::round(std::clamp(p.w * sc, ctx.s(kMinW), std::max(ctx.s(kMinW), ctx.width() - ctx.s(28.0f))));
        }
        const Rml::Vector2f size = doc->GetBox().GetSize(Rml::BoxArea::Border);
        box.h = size.y > 0.0f ? size.y : ctx.s(120.0f);
        const float bar_h = doc->GetElementById("bar") != nullptr
                                ? doc->GetElementById("bar")->GetBox().GetSize(Rml::BoxArea::Border).y
                                : ctx.s(52.0f);
        if (p.placed) {
            box.x = std::round(p.x * sc);
            box.y = std::round(p.y * sc);
        } else {
            // Not placed yet: away from the windows already at its default place.
            // As the old frame did: below the window that is there.
            for (int tries = 0; tries < 32; ++tries) {
                const ui::Rect* hit = nullptr;
                for (const auto* rects : {&shown_, &shown_last_}) {
                    for (const auto& [other, r] : *rects) {
                        if (other != id && std::abs(r.x - box.x) < 4.0f && std::abs(r.y - box.y) < 4.0f) {
                            hit = &r;
                        }
                    }
                }
                if (hit == nullptr) {
                    break;
                }
                box.y += std::max(bar_h, hit->h) + ctx.s(6.0f);
            }
            p.x = box.x / sc;
            p.y = box.y / sc;
            p.placed = true;
        }
        // Always on the screen, below the top bar.
        box.x = std::clamp(box.x, 0.0f, std::max(0.0f, ctx.width() - box.w));
        box.y = std::clamp(box.y, top + tab_h, std::max(top + tab_h, ctx.height() - bar_h));
        doc->SetProperty("left", std::format("{:.0f}px", box.x));
        doc->SetProperty("top", std::format("{:.0f}px", box.y));
        doc->SetProperty("width", std::format("{:.0f}px", box.w));
        shown_[id] = {box.x, box.y - tab_h, box.w, box.h + tab_h};
        bars_[id] = {box.x, box.y - tab_h, box.w, tab_h + bar_h};
        w.box = box;
        w.bar_h = bar_h;
    }
    // Depth: as WindowList says, when it changed.
    std::vector<std::string> order;
    for (const std::string& id : windows_.order()) {
        if (rml_windows_.contains(id) && !windows_.hidden(id)) {
            order.push_back(id);
        }
    }
    if (order != rml_order_) {
        rml_order_ = order;
        for (const std::string& id : order) {
            if (Rml::ElementDocument* doc = rml.document(rml_windows_[id].doc)) {
                doc->PullToFront();
            }
        }
    }
}

void GameHud::ProcessEvent(Rml::Event& ev) {
    GameSession* s = services_.session();
    if (s == nullptr) {
        return;
    }
    // A panel's (phase 125)?
    for (const auto& [pid, panel] : panels_) {
        if (panel.attached == ev.GetCurrentElement()) {
            const std::string key = pid;  // The handler may change the panels.
            panel_event(ev, key);
            return;
        }
    }
    // Which window: the document the listener is on.
    std::string id;
    for (const auto& [wid, w] : rml_windows_) {
        if (w.attached == ev.GetCurrentElement()) {
            id = wid;
        }
    }
    if (id.empty()) {
        return;
    }
    RmlWindow& w = rml_windows_[id];
    WindowList::Place& p = windows_.place(id);
    const Rml::String& type = ev.GetType();
    const float mx = ev.GetParameter<float>("mouse_x", 0.0f);
    const float my = ev.GetParameter<float>("mouse_y", 0.0f);
    const float sc = rml_scale_;
    Rml::Element* part = frame_part(ev.GetTargetElement());
    const Rml::String part_id = part != nullptr ? part->GetId() : Rml::String();
    const int slot = WindowList::is_camera_id(id) && id.size() == 4 ? id[3] - '1' : -1;

    if (type == "mousedown") {
        windows_.raise(id);  // Touched: in front.
        return;
    }
    const WindowList::Object* obj = windows_.object(id);
    const bool rows = obj != nullptr || id == "trade" || id == "army";
    if (type == "change") {
        // A slider or a text field of a window of rows.
        Rml::Element* e = ev.GetTargetElement();
        if (rows && e != nullptr && e->HasAttribute("data-act")) {
            RowInput input;
            input.value = control_value(e);
            input.text = ev.GetParameter<Rml::String>("value", "");
            input.enter = ev.GetParameter<bool>("linebreak", false);
            rml_act(*s, id, e->GetAttribute<int>("data-act", -1), input);
        }
        return;
    }
    if (type == "click" && part == nullptr && rows) {
        // A button of a window of rows.
        for (Rml::Element* e = ev.GetTargetElement(); e != nullptr && e != ev.GetCurrentElement(); e = e->GetParentNode()) {
            if (e->HasAttribute("data-act")) {
                if (e->GetTagName() != "input") {
                    rml_act(*s, id, e->GetAttribute<int>("data-act", -1), RowInput{});
                }
                break;
            }
        }
        return;
    }
    if (type == "click") {
        if (part_id == "view" && obj != nullptr) {
            float x = 0.0f;
            float z = 0.0f;
            if (thing_place(*s, obj->kind, obj->entity, x, z)) {
                services_.focus_camera(x, z);
            }
        } else if (part_id == "camera" && obj != nullptr) {
            open_camera(*s, obj->kind, obj->entity);
        } else if (part_id == "close" && obj != nullptr) {
            closing_.push_back(id);  // frame() lets its selection go with it.
        } else if (part_id == "close") {
            if (bool* open = fixed_open(id)) {
                *open = false;
            } else if (slot >= 0 && slot < kCameraWindows) {
                s->ui().camera_windows[static_cast<std::size_t>(slot)].open = false;
            }
            windows_.close(id);
            save_places();
        } else if (part_id == "pin") {
            windows_.set_pinned(id, !p.pinned);
            save_places();
        } else if (part_id == "minimize") {
            p.minimized = !p.minimized;
            save_places();
        } else if (part != nullptr && part->HasAttribute("data-tab")) {
            windows_.raise(part->GetAttribute<Rml::String>("data-tab", ""));
        }
        return;
    }
    if (type == "mousescroll" && part_id == "picture" && slot >= 0) {
        auto& cw = s->ui().camera_windows[static_cast<std::size_t>(slot)];
        const float wheel = -ev.GetParameter<float>("wheel_delta_y", 0.0f);
        cw.distance = std::clamp(cw.distance * std::pow(0.88f, wheel), 3.0f, 80.0f);
        ev.StopPropagation();
        return;
    }
    if (type == "dragstart") {
        rml_drag_.clear();
        if (part_id == "picture" && slot >= 0) {
            camera_drag_ = slot;
            camera_drag_x_ = mx;
            camera_drag_y_ = my;
        } else if (part_id == "grip" && !p.minimized) {
            rml_drag_ = id;
            rml_resizing_ = true;
        } else if (part_id == "bar") {
            rml_drag_ = id;
            rml_resizing_ = false;
            rml_grab_x_ = mx - w.box.x;
            rml_grab_y_ = my - w.box.y;
            if ((SDL_GetModState() & SDL_KMOD_CTRL) != 0) {
                windows_.leave_group(id);  // Ctrl: out of its group.
            }
        } else if (part != nullptr && part->HasAttribute("data-tab")) {
            // A tab pulled away: out of the stack, under the pointer.
            const std::string tab = part->GetAttribute<Rml::String>("data-tab", "");
            windows_.split(tab);
            WindowList::Place& out = windows_.place(tab);
            rml_grab_x_ = 60.0f * sc;
            rml_grab_y_ = w.bar_h * 0.5f;
            out.x = (mx - rml_grab_x_) / sc;
            out.y = (my - rml_grab_y_) / sc;
            out.placed = true;
            windows_.raise(tab);
            rml_drag_ = tab;
            rml_resizing_ = false;
        }
        return;
    }
    if (type == "drag") {
        if (camera_drag_ >= 0 && camera_drag_ == slot) {
            auto& cw = s->ui().camera_windows[static_cast<std::size_t>(slot)];
            cw.yaw -= (mx - camera_drag_x_) * 0.012f;
            cw.pitch = std::clamp(cw.pitch + (my - camera_drag_y_) * 0.01f, 0.05f, 1.45f);
            camera_drag_x_ = mx;
            camera_drag_y_ = my;
            return;
        }
        if (rml_drag_.empty()) {
            return;
        }
        WindowList::Place& d = windows_.place(rml_drag_);
        const auto found = rml_windows_.find(rml_drag_);
        const ui::Rect box = found != rml_windows_.end() ? found->second.box : ui::Rect{d.x * sc, d.y * sc, 300.0f, 100.0f};
        if (rml_resizing_) {
            d.w = std::clamp(mx - box.x, kMinW * sc, std::max(kMinW * sc, rml_width_)) / sc;
            return;
        }
        ui::Rect moved = box;
        moved.x = mx - rml_grab_x_;
        moved.y = my - rml_grab_y_;
        // Magnets: the screen, the build bar and the other windows.
        std::vector<ui::Rect> others;
        for (const auto& [other, r] : shown_last_) {
            if (other != rml_drag_ && (d.group == 0 || windows_.place(other).group != d.group)) {
                others.push_back(r);
            }
        }
        WindowList::magnets(moved, others, {rml_width_, rml_height_, top_bar_bottom_, build_bar_top_}, kSnap * sc);
        const float dx = moved.x - box.x;
        const float dy = moved.y - box.y;
        d.x = moved.x / sc;
        d.y = moved.y / sc;
        if (found != rml_windows_.end()) {
            found->second.box.x = moved.x;
            found->second.box.y = moved.y;
        }
        // The group moves along.
        if (d.group != 0 && (dx != 0.0f || dy != 0.0f)) {
            for (const auto& [other, r] : shown_last_) {
                WindowList::Place& o = windows_.place(other);
                if (other == rml_drag_ || o.group != d.group) {
                    continue;
                }
                if (!o.placed) {
                    o.x = r.x / sc;
                    o.y = r.y / sc;
                    o.placed = true;
                }
                o.x += dx / sc;
                o.y += dy / sc;
            }
        }
        return;
    }
    if (type == "dragend") {
        camera_drag_ = -1;
        if (rml_drag_.empty()) {
            return;
        }
        const std::string dragged = rml_drag_;
        rml_drag_.clear();
        if (!rml_resizing_) {
            // Released over another window's title: they become tabs of one.
            std::string onto;
            const std::vector<std::string> mine = windows_.tabs(dragged);
            for (const std::string& other : windows_.order()) {  // The one in front wins.
                const auto bar_it = bars_last_.find(other);
                if (other != dragged && bar_it != bars_last_.end() && inside(bar_it->second, mx, my) &&
                    std::find(mine.begin(), mine.end(), other) == mine.end()) {
                    onto = other;
                }
            }
            if (!onto.empty()) {
                windows_.merge(dragged, onto);
            } else {
                // Released touching another window: they dock.
                const auto found = rml_windows_.find(dragged);
                if (found != rml_windows_.end()) {
                    for (const auto& [other, r] : shown_last_) {
                        if (other != dragged && WindowList::touching(found->second.box, r)) {
                            WindowList::Place& o = windows_.place(other);
                            if (!o.placed) {
                                o.x = r.x / sc;
                                o.y = r.y / sc;
                                o.placed = true;
                            }
                            windows_.dock(dragged, other);
                        }
                    }
                }
                windows_.sync_stack(dragged);  // Its tabs stay where it is.
            }
        }
        rml_resizing_ = false;
        save_places();
    }
}

}  // namespace sc
