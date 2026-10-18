// The parts of the HUD that RmlUi draws (phase 121): the top bar, the dock,
// the notices and the minimap with its compass (data/ui/hud). Each has a
// data model filled here every frame from the game (only what changed is
// sent again) and events that do what the old HUD's buttons did.
#include <algorithm>
#include <cmath>
#include <format>

#include <RmlUi/Core/Context.h>
#include <RmlUi/Core/DataModelHandle.h>
#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Event.h>

#include "core/speed.h"
#include "game/game_hud.h"
#include "game/hud_model.h"
#include "game/minimap.h"
#include "game/multiplayer_screens.h"
#include "i18n/translator.h"
#include "net/lockstep.h"
#include "ui/rml/rml_ui.h"

namespace sc {

using i18n::tr;

namespace {

constexpr const char* kTopDoc = "hud/top.rml";
constexpr const char* kDockDoc = "hud/dock.rml";
constexpr const char* kNotesDoc = "hud/notes.rml";
constexpr const char* kMiniDoc = "hud/minimap.rml";
constexpr const char* kBuildDoc = "hud/build.rml";
constexpr const char* kHintDoc = "hud/hint.rml";
constexpr const char* kDocs[] = {kTopDoc, kDockDoc, kNotesDoc, kMiniDoc, kBuildDoc, kHintDoc};

constexpr std::uint64_t kNoteNs = 12'000'000'000;  // A notice stays this long.
constexpr std::size_t kNotesShown = 4;

minimap::Rgba rgba_of(ui::Color c, std::uint8_t alpha = 255) {
    return {c.r, c.g, c.b, alpha};
}

// The element of `doc` with `id`, or null.
Rml::Element* element(rml::RmlUi& rml, const char* doc, const char* id) {
    Rml::ElementDocument* d = rml.document(doc);
    return d != nullptr ? d->GetElementById(id) : nullptr;
}

}  // namespace

void GameHud::rml_models(rml::RmlUi& rml) {
    Rml::Context& c = *rml.context();
    // The top bar.
    if (Rml::DataModelConstructor m = c.CreateDataModel("top")) {
        if (auto item = m.RegisterStruct<HudItem>()) {
            item.RegisterMember("id", &HudItem::id);
            item.RegisterMember("text", &HudItem::text);
            item.RegisterMember("image", &HudItem::image);
            item.RegisterMember("sprite", &HudItem::sprite);
            item.RegisterMember("tip", &HudItem::tip);
        }
        m.RegisterArray<std::vector<HudItem>>();
        m.Bind("founded", &top_.founded);
        m.Bind("goods", &top_.goods);
        m.Bind("hidden", &top_.hidden);
        m.Bind("hidden_tip", &top_.hidden_tip);
        m.Bind("population", &top_.population);
        m.Bind("population_tip", &top_.population_tip);
        m.Bind("happiness", &top_.happiness);
        m.Bind("gold", &top_.gold);
        m.Bind("happiness_tip", &top_.happiness_tip);
        m.Bind("unhappy", &top_.unhappy);
        m.Bind("troubles", &top_.troubles);
        m.Bind("sick", &top_.sick);
        m.Bind("fires", &top_.fires);
        m.Bind("burning", &top_.burning);
        m.Bind("troubles_tip", &top_.troubles_tip);
        m.Bind("raiders", &top_.raiders);
        m.Bind("raiders_text", &top_.raiders_text);
        m.Bind("alarm_text", &top_.alarm_text);
        m.Bind("raiders_tip", &top_.raiders_tip);
        m.Bind("weather", &top_.weather);
        m.Bind("date", &top_.date);
        m.Bind("weather_tip", &top_.weather_tip);
        m.Bind("weather_icon", &top_.weather_icon);
        m.Bind("cold", &top_.cold);
        m.Bind("speed", &top_.speed);
        m.Bind("paused", &top_.paused);
        m.Bind("can_slower", &top_.can_slower);
        m.Bind("can_faster", &top_.can_faster);
        m.Bind("networked", &top_.networked);
        m.Bind("players", &top_.players);
        m.Bind("players_tip", &top_.players_tip);
        m.BindEventCallback("pause", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList&) {
            const int now = services_.game_speed();
            services_.set_game_speed(now == speed::kPause ? shown_speed_ : speed::kPause);
        });
        m.BindEventCallback("slower", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList&) {
            if (shown_speed_ > speed::kMin) {
                services_.set_game_speed(speed::slower(shown_speed_));
            }
        });
        m.BindEventCallback("faster", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList&) {
            const int most = services_.max_game_speed();
            if (shown_speed_ < most) {
                services_.set_game_speed(speed::faster(shown_speed_, most));
            }
        });
        top_model_ = m.GetModelHandle();
    }
    // The dock.
    if (Rml::DataModelConstructor m = c.CreateDataModel("dock")) {
        if (auto e = m.RegisterStruct<DockEntry>()) {
            e.RegisterMember("id", &DockEntry::id);
            e.RegisterMember("label", &DockEntry::label);
            e.RegisterMember("tip", &DockEntry::tip);
            e.RegisterMember("icon", &DockEntry::icon);
            e.RegisterMember("mark", &DockEntry::mark);
            e.RegisterMember("open", &DockEntry::open);
        }
        m.RegisterArray<std::vector<DockEntry>>();
        m.Bind("entries", &dock_);
        m.BindEventCallback("toggle", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            if (!args.empty()) {
                toggle_dock(args[0].Get<Rml::String>());
            }
        });
        dock_model_ = m.GetModelHandle();
    }
    // The notices.
    if (Rml::DataModelConstructor m = c.CreateDataModel("notes")) {
        if (auto n = m.RegisterStruct<HudNote>()) {
            n.RegisterMember("text", &HudNote::text);
            n.RegisterMember("tip", &HudNote::tip);
            n.RegisterMember("has_pos", &HudNote::has_pos);
        }
        m.RegisterArray<std::vector<HudNote>>();
        m.Bind("notes", &notes_shown_);
        m.BindEventCallback("go", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            if (args.empty()) {
                return;
            }
            const int i = args[0].Get<int>(-1);
            if (i >= 0 && static_cast<std::size_t>(i) < notes_index_.size()) {
                const Note& n = notes_[notes_index_[static_cast<std::size_t>(i)]];
                if (n.has_pos) {
                    services_.focus_camera(n.x, n.z);
                }
            }
        });
        notes_model_ = m.GetModelHandle();
    }
    // The minimap and the compass.
    if (Rml::DataModelConstructor m = c.CreateDataModel("mini")) {
        m.Bind("needle", &needle_);
        m.Bind("n_left", &needle_n_left_);
        m.Bind("n_top", &needle_n_top_);
        const auto to_map = [this](Rml::Event& ev) {
            GameSession* s = services_.session();
            Rml::Element* e = ev.GetCurrentElement();
            if (s == nullptr || e == nullptr || s->game().map().size <= 0) {
                return;
            }
            const Rml::Vector2f at = e->GetAbsoluteOffset(Rml::BoxArea::Content);
            const Rml::Vector2f size = e->GetBox().GetSize(Rml::BoxArea::Content);
            if (size.x <= 0.0f || size.y <= 0.0f) {
                return;
            }
            const auto n = static_cast<float>(s->game().map().size);
            const float x = std::clamp((ev.GetParameter<float>("mouse_x", 0.0f) - at.x) / size.x * n, 0.0f, n);
            const float z = std::clamp((ev.GetParameter<float>("mouse_y", 0.0f) - at.y) / size.y * n, 0.0f, n);
            services_.focus_camera(x, z);
        };
        m.BindEventCallback("map_press", [to_map](Rml::DataModelHandle, Rml::Event& ev, const Rml::VariantList&) {
            if (ev.GetParameter<int>("button", 0) == 0) {
                to_map(ev);
            }
        });
        m.BindEventCallback("map_drag", [to_map](Rml::DataModelHandle, Rml::Event& ev, const Rml::VariantList&) {
            to_map(ev);
        });
        m.BindEventCallback("map_release", [](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList&) {});
        mini_model_ = m.GetModelHandle();
    }
    // The build bar.
    if (Rml::DataModelConstructor m = c.CreateDataModel("build")) {
        if (auto item = m.RegisterStruct<HudItem>()) {
            item.RegisterMember("text", &HudItem::text);
            item.RegisterMember("image", &HudItem::image);
            item.RegisterMember("sprite", &HudItem::sprite);
            item.RegisterMember("tip", &HudItem::tip);
        }
        m.RegisterArray<std::vector<HudItem>>();
        if (auto cat = m.RegisterStruct<BuildCat>()) {
            cat.RegisterMember("index", &BuildCat::index);
            cat.RegisterMember("name", &BuildCat::name);
            cat.RegisterMember("icon", &BuildCat::icon);
            cat.RegisterMember("mark", &BuildCat::mark);
            cat.RegisterMember("on", &BuildCat::on);
        }
        m.RegisterArray<std::vector<BuildCat>>();
        if (auto item = m.RegisterStruct<BuildItem>()) {
            item.RegisterMember("id", &BuildItem::id);
            item.RegisterMember("name", &BuildItem::name);
            item.RegisterMember("image", &BuildItem::image);
            item.RegisterMember("cost", &BuildItem::cost);
            item.RegisterMember("tip", &BuildItem::tip);
            item.RegisterMember("lock", &BuildItem::lock);
            item.RegisterMember("mark", &BuildItem::mark);
            item.RegisterMember("on", &BuildItem::on);
        }
        m.RegisterArray<std::vector<BuildItem>>();
        m.Bind("cats", &build_.cats);
        m.Bind("items", &build_.items);
        m.BindEventCallback("category", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            if (!args.empty()) {
                category_ = static_cast<std::uint8_t>(std::clamp(args[0].Get<int>(0), 0, static_cast<int>(kBuildCategories) - 1));
            }
        });
        m.BindEventCallback("place", [this](Rml::DataModelHandle, Rml::Event&, const Rml::VariantList& args) {
            GameSession* s = services_.session();
            if (args.empty() || s == nullptr) {
                return;
            }
            const sim::Game& game = s->game();
            const sim::DefIndex def = game.content().find_building(args[0].Get<Rml::String>());
            if (def == sim::kNoDef || game.content().buildings[def].tier > game.tier(s->town())) {
                return;  // Locked.
            }
            GameSession::Interaction& ui = s->ui();
            ui.placing = ui.placing == def ? sim::kNoDef : def;
            ui.clear_selection();
        });
        build_model_ = m.GetModelHandle();
    }
    // The placing hint.
    if (Rml::DataModelConstructor m = c.CreateDataModel("hint")) {
        m.Bind("shown", &hint_shown_);
        m.Bind("text", &hint_text_);
        m.Bind("bad", &hint_bad_);
        hint_model_ = m.GetModelHandle();
    }
    rml_ready_ = true;
}

void GameHud::toggle_dock(const std::string& id) {
    bool* open = id == "goods"    ? &goods_open_
                 : id == "stats"  ? &stats_open_
                 : id == "log"    ? &log_open_
                 : id == "layers" ? &layers_open_
                 : id == "trade"  ? &trade_open_
                 : id == "army"   ? &army_open_
                                  : nullptr;
    if (open == nullptr) {
        return;
    }
    if (*open && windows_.place(id).pinned) {
        open_window(id);  // Pinned: only its own X closes it.
    } else {
        *open = !*open;
        if (*open) {
            open_window(id);
        }
    }
}

void GameHud::hide_rml() {
    rml::RmlUi* rml = services_.rml();
    if (rml == nullptr) {
        return;
    }
    for (const char* doc : kDocs) {
        if (rml->document_shown(doc)) {
            (void)rml->show_document(doc, false);
        }
    }
    rml->set_mark({});
}

void GameHud::rml_frame(ui::Context& ctx, GameSession& s) {
    rml::RmlUi* rml = services_.rml();
    if (rml == nullptr) {
        top_bar_bottom_ = std::round(ctx.s(52.0f));
        right_top_ = top_bar_bottom_;
        return;
    }
    if (!rml_ready_) {
        rml_models(*rml);
    }
    const sim::Game& game = s.game();
    const bool town = s.game().founded(s.local_player()) && !s.spectating();
    for (const char* doc : kDocs) {
        if (!rml->document_shown(doc) && (town || doc != std::string_view(kBuildDoc))) {
            (void)rml->show_document(doc, true);
        }
    }
    rml->set_mark(highlight_);

    // The top bar.
    const int now = services_.game_speed();
    if (now != speed::kPause) {
        shown_speed_ = now;  // What "xN" says while paused, and where the pause goes back to.
    }
    HudNetInfo net;
    if (net::NetSession* n = services_.net(); n != nullptr && s.networked()) {
        net.networked = true;
        for (const net::LobbyPlayer& p : n->lobby().players) {
            net.connected += p.connected ? 1 : 0;
            net.names += (net.names.empty() ? "" : "\n") + tr(p.connected ? "hud.net.player" : "hud.net.playerAway", p.name) +
                         (p.watching && p.connected ? " " + tr("hud.net.watching") : std::string());
        }
        for (const std::string& w : n->lobby().watchers) {
            net.names += (net.names.empty() ? "" : "\n") + tr("hud.net.player", w) + " " + tr("hud.net.watching");
        }
    }
    TopBarModel top = top_bar_model(game, s.town(), s.local_player(), now, shown_speed_, services_.max_game_speed(), net);
    if (!(top == top_)) {
        top_ = std::move(top);
        top_model_.DirtyAllVariables();
    }

    // The dock: the town's windows (phase 74: none before the town).
    std::vector<DockEntry> dock;
    if (game.founded(s.local_player()) && !s.spectating()) {
        bool others = false;
        bool barracks = false;
        for (std::uint8_t p = 0; p < game.player_count(); ++p) {
            others = others || (game.town_exists(p) && p != s.town());
        }
        for (const sim::Building& b : game.buildings().data()) {
            barracks = barracks || (b.owner == s.town() && game.content().buildings[b.def].trains);
        }
        const struct {
            const char* id;
            const char* label;
            const char* tip;
            const char* icon;
            bool open;
            bool shown;
        } entries[] = {
            {"goods", "hud.dock.goods", "hud.dock.goods.tooltip", "icon-box", goods_open_, true},
            {"stats", "hud.dock.stats", "hud.dock.stats.tooltip", "icon-chart", stats_open_, true},
            {"log", "hud.dock.log", "hud.dock.log.tooltip", "icon-list", log_open_, true},
            {"layers", "hud.dock.layers", "hud.dock.layers.tooltip", "icon-layers", layers_open_, true},
            {"trade", "hud.trade", "hud.trade.tooltip", "icon-scales", trade_open_, others},
            {"army", "hud.dock.army", "hud.army.tooltip", "icon-swords", army_open_,
             barracks || game.soldiers(s.town()) > 0},
        };
        for (const auto& e : entries) {
            if (!e.shown) {
                continue;
            }
            DockEntry d;
            d.id = e.id;
            d.label = std::string_view(e.id) == "army" ? tr("hud.army", game.soldiers(s.town())) : tr(e.label);
            d.tip = d.label + "\n" + tr(e.tip);
            d.icon = e.icon;
            d.mark = std::string("dock:") + e.id;
            d.open = e.open;
            dock.push_back(std::move(d));
        }
    }
    if (!(dock == dock_)) {
        dock_ = std::move(dock);
        dock_model_.DirtyAllVariables();
    }

    // The notices: the last few, newest at the bottom, over the build bar.
    std::vector<HudNote> shown;
    std::vector<std::size_t> index;
    for (std::size_t k = notes_.size(); k-- > 0 && shown.size() < kNotesShown;) {
        const Note& n = notes_[k];
        if (ctx.now_ns() - n.at_ns > kNoteNs) {
            break;
        }
        HudNote h;
        h.text = n.count > 1 ? n.text + " (×" + std::to_string(n.count) + ")" : n.text;
        h.has_pos = n.has_pos;
        h.tip = n.has_pos ? tr("hud.log.goTo") : std::string();
        shown.insert(shown.begin(), std::move(h));
        index.insert(index.begin(), k);
    }
    notes_index_ = std::move(index);
    if (!(shown == notes_shown_)) {
        notes_shown_ = std::move(shown);
        notes_model_.DirtyAllVariables();
    }
    if (Rml::ElementDocument* d = rml->document(kNotesDoc)) {
        const float bottom = std::max(0.0f, ctx.height() - build_bar_top_ + std::round(ctx.s(8.0f)));
        d->SetProperty("bottom", std::format("{:.1f}px", bottom));
    }

    rml_minimap(ctx, s, *rml);

    // The build bar: only with a town to build for (phase 74; phase 79: not
    // for whoever watches).
    const bool has_town = game.founded(s.local_player()) && !s.spectating();
    if (!has_town && rml->document_shown(kBuildDoc)) {
        (void)rml->show_document(kBuildDoc, false);
    }
    BuildBarModel build = has_town ? build_bar_model(game, s.town(), category_, s.ui().placing, highlight_) : BuildBarModel{};
    if (!(build == build_)) {
        build_ = std::move(build);
        build_model_.DirtyAllVariables();
    }
    build_bar_top_ = ctx.height();
    if (Rml::ElementDocument* bar = has_town ? rml->document(kBuildDoc) : nullptr) {
        if (Rml::Element* panel = bar->GetFirstChild()) {
            build_bar_top_ = panel->GetAbsoluteOffset(Rml::BoxArea::Border).y;
        }
    }
    // The hint over it, while placing or marking.
    bool bad = false;
    const bool hint = s.ui().placing != sim::kNoDef || s.ui().field_farm.valid();
    std::string text = hint ? placement_text(s, bad) : std::string();
    if (hint != hint_shown_ || text != hint_text_ || bad != hint_bad_) {
        hint_shown_ = hint;
        hint_text_ = std::move(text);
        hint_bad_ = bad;
        hint_model_.DirtyAllVariables();
    }
    if (Rml::ElementDocument* d = rml->document(kHintDoc)) {
        d->SetProperty("bottom", std::format("{:.1f}px", std::max(0.0f, ctx.height() - build_bar_top_ + std::round(ctx.s(8.0f)))));
    }

    // Where the old parts lay out from: under the top bar, under the minimap.
    if (Rml::ElementDocument* d = rml->document(kTopDoc)) {
        const float bottom = d->GetAbsoluteOffset(Rml::BoxArea::Border).y + d->GetBox().GetSize(Rml::BoxArea::Border).y;
        top_bar_bottom_ = std::max(bottom, std::round(ctx.s(40.0f)));
    }
    if (Rml::ElementDocument* d = rml->document(kMiniDoc)) {
        right_top_ = d->GetAbsoluteOffset(Rml::BoxArea::Border).y + d->GetBox().GetSize(Rml::BoxArea::Border).y +
                     std::round(ctx.s(10.0f));
    }
}

void GameHud::rml_minimap(ui::Context& ctx, GameSession& s, rml::RmlUi& rml) {
    const sim::Game& game = s.game();
    const sim::MapData& map = game.map();
    if (map.size <= 0) {
        return;
    }
    // The ground, made again only for another map; the fog over it when it
    // changed, at most a few times a second.
    const FogView& fog = s.fog();
    bool redraw = false;
    if (minimap_session_ != &s || !(minimap_settings_ == map.settings)) {
        minimap_base_ = minimap::render(map);
        minimap_session_ = &s;
        minimap_settings_ = map.settings;
        redraw = true;
    }
    const int fog_mode = static_cast<int>(fog.mode());
    // Phase 74: with no town yet, the fog lets the shape of the land show.
    const bool silhouette = !game.founded(s.local_player());
    if (silhouette != minimap_silhouette_) {
        minimap_silhouette_ = silhouette;
        redraw = true;
    }
    if (fog_mode != minimap_fog_mode_ || fog.generation() != minimap_fog_generation_) {
        redraw = true;
    } else if (fog.revision() != minimap_fog_revision_ && ctx.now_ns() - minimap_fog_ns_ > 250'000'000ull) {
        redraw = true;
    }
    if (redraw) {
        minimap_fogged_ = minimap_base_;
        minimap::apply_fog(minimap_fogged_, map.size, fog, silhouette);
        minimap_fog_mode_ = fog_mode;
        minimap_fog_generation_ = fog.generation();
        minimap_fog_revision_ = fog.revision();
        minimap_fog_ns_ = ctx.now_ns();
    }
    // What lies over it: drawn again when the camera moved, the ground
    // changed, or a few times a second (buildings come and go).
    const Services::CameraGround view = services_.camera_ground();
    if (redraw || view.corners != minimap_corners_ || ctx.now_ns() - minimap_drawn_ns_ > 200'000'000ull) {
        minimap_corners_ = view.corners;
        minimap_drawn_ns_ = ctx.now_ns();
        std::vector<std::uint8_t> image = minimap_fogged_;
        const float scale = static_cast<float>(minimap::kImageSize) / static_cast<float>(map.size);
        // Phase 95: the roads; under the fog of war, the explored ones.
        if (!game.roads().empty()) {
            const auto side = static_cast<std::uint32_t>(game.road_side());
            const float cell = static_cast<float>(sim::kRoadModule) * scale;
            for (const auto& [index, kind] : game.roads()) {
                const float x = static_cast<float>(index % side) * static_cast<float>(sim::kRoadModule);
                const float z = static_cast<float>(index / side) * static_cast<float>(sim::kRoadModule);
                if (fog.mode() != sim::FogMode::None && !fog.explored(x + 1.0f, z + 1.0f)) {
                    continue;
                }
                minimap::fill(image, x * scale, z * scale, std::max(1.0f, cell), std::max(1.0f, cell),
                              {0xD8, 0xC4, 0x9A, 230});
            }
        }
        // Buildings in their town's color, at least a dot.
        constexpr float kDot = 2.0f;
        for (const sim::Building& b : game.buildings().data()) {
            if (fog.mode() != sim::FogMode::None && game.town_group(b.owner) != fog.group() &&
                !fog.rect_shows(b.x, b.z, b.width, b.depth)) {
                continue;  // Under the fog of war.
            }
            minimap::fill(image, static_cast<float>(b.x) * scale, static_cast<float>(b.z) * scale,
                          std::max(kDot, static_cast<float>(b.width) * scale), std::max(kDot, static_cast<float>(b.depth) * scale),
                          rgba_of(player_color(b.owner)));
        }
        // Dynamic fog: others' buildings out of sight as last seen (phase 33).
        if (fog.mode() == sim::FogMode::Dynamic) {
            for (const sim::BuildingGhost& g : game.vision().ghosts(fog.group())) {
                const sim::Building* real = game.buildings().get(g.id);
                if ((real != nullptr && fog.rect_in_sight(real->x, real->z, real->width, real->depth)) ||
                    g.def >= game.content().buildings.size()) {
                    continue;
                }
                std::int32_t gw = 0;
                std::int32_t gd = 0;
                sim::Game::footprint(game.content().buildings[g.def], g.rotation, gw, gd);
                minimap::fill(image, static_cast<float>(g.x) * scale, static_cast<float>(g.z) * scale,
                              std::max(kDot, static_cast<float>(gw) * scale), std::max(kDot, static_cast<float>(gd) * scale),
                              rgba_of(player_color(g.owner), 180));
            }
        }
        // Phase 74: with a town to found, the suggested sites, fog or no fog.
        if (choosing_site(game, s.ui(), s.local_player())) {
            const ui::Color accent = ctx.theme().accent;
            for (std::size_t i = 0; i < map.starts.size(); ++i) {
                if (game.site_taken(i)) {
                    continue;
                }
                const float x = static_cast<float>(map.starts[i].x.raw()) / 65536.0f * scale;
                const float z = static_cast<float>(map.starts[i].z.raw()) / 65536.0f * scale;
                minimap::fill(image, x - 4.5f, z - 4.5f, 9.0f, 9.0f, {0, 0, 0, 200});
                minimap::fill(image, x - 3.5f, z - 3.5f, 7.0f, 7.0f, rgba_of(accent));
            }
        }
        // What the camera sees.
        for (int i = 0; i < 4; ++i) {
            const int j = (i + 1) % 4;
            minimap::line(image, view.corners[static_cast<std::size_t>(i) * 2] * scale,
                          view.corners[static_cast<std::size_t>(i) * 2 + 1] * scale,
                          view.corners[static_cast<std::size_t>(j) * 2] * scale,
                          view.corners[static_cast<std::size_t>(j) * 2 + 1] * scale, 1.5f, {255, 255, 255, 220});
        }
        services_.set_hud_image("minimap", minimap::kImageSize, minimap::kImageSize, image);
    }

    // The compass: its needle turns with the camera, the N at its head.
    const std::array<float, 2> north = minimap::north_on_screen(view.yaw);
    const float degrees = std::atan2(north[0], -north[1]) * 180.0f / 3.14159265f;
    const std::string needle = std::format("rotate({:.1f}deg)", degrees);
    // The compass is 64 dp; the N goes 24 dp from its middle, 16 dp wide.
    const std::string n_left = std::format("{:.1f}dp", 32.0f + north[0] * 24.0f - 8.0f);
    const std::string n_top = std::format("{:.1f}dp", 32.0f + north[1] * 24.0f - 8.0f);
    if (needle != needle_ || n_left != needle_n_left_ || n_top != needle_n_top_) {
        needle_ = needle;
        needle_n_left_ = n_left;
        needle_n_top_ = n_top;
        mini_model_.DirtyAllVariables();
    }
    // Where the map's picture is, for the explorer's right click (app.cpp).
    if (Rml::Element* e = element(rml, kMiniDoc, "map")) {
        const Rml::Vector2f at = e->GetAbsoluteOffset(Rml::BoxArea::Content);
        const Rml::Vector2f size = e->GetBox().GetSize(Rml::BoxArea::Content);
        s.ui().minimap = {at.x, at.y, size.x, size.y};
    }
}

}  // namespace sc
