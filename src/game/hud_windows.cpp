// The game windows' frame (section 6.4, phase 62): one in front of another
// (the one touched comes forward and only the one in front gets the click),
// moved by the title bar, drawn to the screen edges, the build bar and each
// other like magnets, docked in groups that move together, minimized to
// their title, pinned to stay open, wider or narrower by the corner grip,
// and remembered in settings.json (game/window_list.h keeps the list).
// Also the launcher on the left, the goods, statistics, event log and map
// layers windows, and the notifications.
#include <algorithm>
#include <cmath>

#include <SDL3/SDL_keyboard.h>

#include "game/game_hud.h"
#include "i18n/translator.h"
#include "net/lockstep.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 44.0f;
constexpr float kDockW = 132.0f;
constexpr float kSnap = 12.0f;
constexpr std::uint64_t kNoteNs = 12'000'000'000;

bool inside(const ui::Rect& r, float x, float y) {
    return x >= r.x && y >= r.y && x < r.right() && y < r.bottom();
}

}  // namespace

void GameHud::save_places() {
    const std::string text = windows_.save();
    if (text.empty() && !windows_.places().empty() && !services_.settings().ui.windows.empty()) {
        // Nothing to keep, or it would not fit: an empty layout is still a layout.
        bool any = false;
        for (const auto& [id, w] : windows_.places()) {
            any = any || (!WindowList::is_object_id(id) && (w.placed || w.pinned));
        }
        if (any) {
            return;
        }
    }
    if (services_.settings().ui.windows != text) {
        services_.settings().ui.windows = text;
        services_.settings_changed();
    }
}

void GameHud::windows_begin(ui::Context& ctx) {
    if (!places_loaded_) {
        places_loaded_ = true;
        windows_.load(services_.settings().ui.windows);
    }
    shown_last_ = std::move(shown_);
    shown_.clear();
    // The window the cursor is over: the only one that hears the mouse.
    const ui::Input& in = ctx.input();
    hover_top_ = dragging_.empty() ? windows_.top_at(shown_last_, in.mouse_x, in.mouse_y) : dragging_;
}

void GameHud::windows_end(ui::Context& ctx) {
    const ui::Input& in = ctx.input();
    if (!in.mouse_down && !dragging_.empty()) {
        dragging_.clear();
        resizing_ = false;
        save_places();
    }
}

bool GameHud::window(ui::Context& ctx, GameSession& s, const std::string& id, const std::string& title, ui::Rect& box,
                     bool& open) {
    WindowList::Place& p = windows_.place(id);
    const float sc = ctx.s(1.0f);
    const float pad = ctx.s(14.0f);
    const ui::TextStyle title_style = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float title_h = ctx.text().line_height(title_style);
    const float bar_h = std::round(pad + title_h + pad * 0.5f);
    const float button = std::round(ctx.s(34.0f));
    const float min_w = ctx.s(280.0f);
    const float gap = ctx.s(6.0f);
    const ui::Input& in = ctx.input();
    const bool live = !ctx.input_blocked();
    const float top = std::round(ctx.s(kTopBarH));

    if (p.w > 0.0f) {
        box.w = std::round(std::clamp(p.w * sc, min_w, std::max(min_w, ctx.width() - 2 * pad)));
    }
    if (p.placed) {
        box.x = std::round(p.x * sc);
        box.y = std::round(p.y * sc);
    } else {
        // Not placed yet: away from the windows already at its default
        // place. The windows of things go beside each other while there is
        // room, the others below.
        const bool beside = WindowList::is_object_id(id);
        for (int tries = 0; tries < 2 * static_cast<int>(WindowList::kMaxObjects); ++tries) {
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
            if (beside && box.x - box.w - gap >= left_x(ctx)) {
                box.x -= box.w + gap;
            } else {
                box.y += beside ? bar_h : std::max(bar_h + gap, hit->h + gap);
            }
        }
        // From now on it stays there (until the player moves it).
        p.x = box.x / sc;
        p.y = box.y / sc;
        p.placed = true;
    }
    if (p.minimized) {
        box.h = bar_h;
    }
    // Always on the screen, below the top bar.
    box.x = std::clamp(box.x, 0.0f, std::max(0.0f, ctx.width() - box.w));
    box.y = std::clamp(box.y, top, std::max(top, ctx.height() - bar_h));

    // Solid: what lies behind a window does not show through it.
    ui::Color solid = ctx.theme().panel;
    solid.a = 255;
    ctx.draw().rect(box, solid);
    ctx.panel(box);
    block(s, box);
    shown_[id] = box;
    if (live && in.mouse_pressed && inside(box, in.mouse_x, in.mouse_y)) {
        windows_.raise(id);  // Touched: in front from the next frame.
    }
    // Title, minimize, pin and close.
    const float pin_w = std::round(ctx.s(64.0f));
    const float buttons = button + gap + pin_w + gap + button;
    ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad - buttons - gap, title_h}, title, title_style, ctx.theme().accent);
    const float by = box.y + std::round((bar_h - button) * 0.5f) + (p.minimized ? 0.0f : ctx.s(2.0f));
    const bool pinned = p.pinned;
    bool closed = false;
    if (ctx.button(ctx.id("minimize"), {box.right() - pad - buttons, by, button, button},
                   tr(p.minimized ? "hud.window.restore" : "hud.window.minimize"),
                   tr(p.minimized ? "hud.window.restore.tooltip" : "hud.window.minimize.tooltip"))) {
        p.minimized = !p.minimized;
        save_places();
    }
    if (ctx.button(ctx.id("pin"), {box.right() - pad - button - gap - pin_w, by, pin_w, button},
                   tr(pinned ? "hud.window.pinned" : "hud.window.pin"), tr("hud.window.pin.tooltip"), true, pinned)) {
        windows_.set_pinned(id, !pinned);
        save_places();
    }
    if (ctx.button(ctx.id("close"), {box.right() - pad - button, by, button, button}, tr("hud.close"),
                   tr("hud.window.close.tooltip"))) {
        open = false;
        closed = true;
    }

    // Moving by the title bar (with its group), resizing by the corner.
    const ui::Rect bar{box.x, box.y, box.w - buttons - pad - gap, bar_h};
    const ui::Rect grip{box.right() - ctx.s(16.0f), box.bottom() - ctx.s(16.0f), ctx.s(16.0f), ctx.s(16.0f)};
    if (!p.minimized) {
        ctx.draw().rect({grip.x + ctx.s(6.0f), grip.bottom() - ctx.s(4.0f), ctx.s(8.0f), ctx.s(2.0f)},
                        ctx.theme().panel_border);
        ctx.draw().rect({grip.right() - ctx.s(4.0f), grip.y + ctx.s(6.0f), ctx.s(2.0f), ctx.s(8.0f)},
                        ctx.theme().panel_border);
    }
    if (live && in.mouse_pressed && dragging_.empty() && !closed) {
        if (!p.minimized && inside(grip, in.mouse_x, in.mouse_y)) {
            dragging_ = id;
            resizing_ = true;
        } else if (inside(bar, in.mouse_x, in.mouse_y)) {
            dragging_ = id;
            resizing_ = false;
            grab_x_ = in.mouse_x - box.x;
            grab_y_ = in.mouse_y - box.y;
            if ((SDL_GetModState() & SDL_KMOD_CTRL) != 0) {
                windows_.leave_group(id);  // Ctrl: out of its group.
            }
        }
    }
    if (dragging_ == id && in.mouse_down) {
        if (resizing_) {
            p.w = std::clamp(in.mouse_x - box.x, min_w, ctx.width()) / sc;
            box.w = std::round(p.w * sc);
        } else {
            ui::Rect moved = box;
            moved.x = in.mouse_x - grab_x_;
            moved.y = in.mouse_y - grab_y_;
            // Magnets: the screen, the build bar and the other windows.
            std::vector<ui::Rect> others;
            for (const auto& [other, r] : shown_last_) {
                if (other != id && (p.group == 0 || windows_.place(other).group != p.group)) {
                    others.push_back(r);
                }
            }
            WindowList::magnets(moved, others, {ctx.width(), ctx.height(), top, build_bar_top_}, kSnap * sc);
            const float dx = moved.x - box.x;
            const float dy = moved.y - box.y;
            box.x = moved.x;
            box.y = moved.y;
            p.x = box.x / sc;
            p.y = box.y / sc;
            // The group moves along.
            if (p.group != 0 && (dx != 0.0f || dy != 0.0f)) {
                for (const auto& [other, r] : shown_last_) {
                    WindowList::Place& w = windows_.place(other);
                    if (other == id || w.group != p.group) {
                        continue;
                    }
                    if (!w.placed) {
                        w.x = r.x / sc;
                        w.y = r.y / sc;
                        w.placed = true;
                    }
                    w.x += dx / sc;
                    w.y += dy / sc;
                }
            }
        }
    }
    // Released touching another window: they dock.
    if (dragging_ == id && !in.mouse_down && !resizing_) {
        for (const auto& [other, r] : shown_last_) {
            if (other != id && WindowList::touching(box, r)) {
                WindowList::Place& o = windows_.place(other);
                if (!o.placed) {
                    o.x = r.x / sc;
                    o.y = r.y / sc;
                    o.placed = true;
                }
                windows_.dock(id, other);
            }
        }
    }
    return !closed && !windows_.place(id).minimized;
}

void GameHud::open_window(const std::string& id) {
    windows_.raise(id);
}

// --- The launcher on the left -----------------------------------------------------------------

void GameHud::dock(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const float pad = ctx.s(12.0f);
    const float w = std::round(ctx.s(kDockW - 12.0f));
    const float h = std::round(ctx.s(30.0f));
    const float gap = ctx.s(4.0f);
    float y = std::round(ctx.s(kTopBarH) + pad);
    struct Entry {
        const char* id;
        const char* label;
        const char* tooltip;
        bool* open;
        bool shown;
    };
    bool others = false;
    bool barracks = false;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        others = others || (game.town_of(p) == p && p != s.town() && game.player(p).active);
    }
    for (const sim::Building& b : game.buildings().data()) {
        barracks = barracks || (b.owner == s.town() && game.content().buildings[b.def].trains);
    }
    const Entry entries[] = {
        {"goods", "hud.dock.goods", "hud.dock.goods.tooltip", &goods_open_, true},
        {"stats", "hud.dock.stats", "hud.dock.stats.tooltip", &stats_open_, true},
        {"log", "hud.dock.log", "hud.dock.log.tooltip", &log_open_, true},
        {"layers", "hud.dock.layers", "hud.dock.layers.tooltip", &layers_open_, true},
        {"trade", "hud.trade", "hud.trade.tooltip", &trade_open_, others},
        {"army", "hud.dock.army", "hud.army.tooltip", &army_open_, barracks || game.soldiers(s.town()) > 0},
    };
    for (const Entry& e : entries) {
        if (!e.shown) {
            continue;
        }
        const ui::Rect r{pad, y, w, h};
        block(s, r);
        if (highlight_ == std::string("dock:") + e.id) {
            mark(ctx, r);
        }
        std::string label = tr(e.label);
        if (std::string_view(e.id) == "army") {
            label = tr("hud.army", game.soldiers(s.town()));
        }
        if (ctx.button(ctx.id(std::string("dock_") + e.id), r, label, tr(e.tooltip), true, *e.open)) {
            if (*e.open && windows_.place(e.id).pinned) {
                open_window(e.id);  // Pinned: only its own X closes it.
            } else {
                *e.open = !*e.open;
                if (*e.open) {
                    open_window(e.id);
                }
            }
        }
        y += h + gap;
    }
}

float GameHud::left_x(ui::Context& ctx) const {
    return std::round(ctx.s(kDockW + 8.0f));
}

// --- Goods, statistics, event log, layers ------------------------------------------------------

void GameHud::goods_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(small) + ctx.s(2.0f);
    const float head = ctx.text().line_height(body);
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const std::vector<std::int32_t> stored = game.stored(s.town());
    static constexpr const char* kCats[] = {"hud.goods.food", "hud.goods.material", "hud.goods.fuel", "hud.goods.good"};
    // What the town has, in two columns per category.
    float rows = 0.0f;
    for (std::size_t c = 0; c < std::size(kCats); ++c) {
        std::size_t n = 0;
        for (std::size_t r = 0; r < stored.size(); ++r) {
            n += static_cast<std::size_t>(content.resources[r].category) == c && stored[r] > 0 ? 1 : 0;
        }
        rows += n > 0 ? head + static_cast<float>((n + 1) / 2) * line : 0.0f;
    }
    rows = std::max(rows, line);
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(std::min(ctx.s(440.0f), ctx.width() - 2 * pad)),
                 std::round(pad + title_h + pad * 0.5f + rows + pad)};
    bool open = true;
    if (!window(ctx, s, "goods", tr("hud.goods.title"), box, open)) {
        goods_open_ = open;
        return;
    }
    goods_open_ = open;
    float y = box.y + pad + title_h + pad * 0.5f;
    const float col = (box.w - 2 * pad) * 0.5f;
    bool any = false;
    for (std::size_t c = 0; c < std::size(kCats); ++c) {
        bool has = false;
        for (std::size_t r = 0; r < stored.size(); ++r) {
            has = has || (static_cast<std::size_t>(content.resources[r].category) == c && stored[r] > 0);
        }
        if (!has) {
            continue;
        }
        any = true;
        ctx.label({box.x + pad, y, box.w - 2 * pad, head}, tr(kCats[c]), body, ctx.theme().accent);
        y += head;
        int k = 0;
        for (std::size_t r = 0; r < stored.size(); ++r) {
            const sim::ResourceDef& d = content.resources[r];
            if (static_cast<std::size_t>(d.category) != c || stored[r] <= 0) {
                continue;
            }
            const ui::Rect cell{box.x + pad + static_cast<float>(k % 2) * col, y, col, line};
            ctx.label(cell, tr("hud.amount", tr(d.name_key), stored[r]), small,
                      stored[r] > 0 ? ctx.theme().text : ctx.theme().text_dim);
            std::string tip = tr(d.name_key) + "\n" + tr("hud.goods.value", d.value);
            if (d.nutrition > 0) {
                tip += "\n" + tr("hud.goods.nutrition", d.nutrition);
            }
            ctx.tooltip_area(ctx.id(d.id), cell, tip);
            if (++k % 2 == 0) {
                y += line;
            }
        }
        if (k % 2 == 1) {
            y += line;
        }
    }
    if (!any) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.goods.none"), small, ctx.theme().text_dim);
    }
}

void GameHud::stats_window(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const std::uint8_t town = s.town();
    const sim::PlayerState& ps = game.player(town);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float pad = ctx.s(14.0f);
    const float line = ctx.text().line_height(body);
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const std::int32_t pop = game.population(town);
    const std::int32_t adults = game.population(town, true);
    // How many of each people.
    std::string peoples;
    const auto& races = game.content().races;
    std::vector<std::int32_t> per_race(races.size(), 0);
    for (const sim::Villager& v : game.villagers().data()) {
        if (v.owner == town && v.race < per_race.size()) {
            ++per_race[v.race];
        }
    }
    for (std::size_t r = 0; r < races.size(); ++r) {
        if (per_race[r] > 0) {
            peoples += (peoples.empty() ? "" : ", ") + tr("hud.amount", tr(races[r].name_key), per_race[r]);
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
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(std::min(ctx.s(380.0f), ctx.width() - 2 * pad)),
                 std::round(pad + title_h + pad * 0.5f + static_cast<float>(lines.size()) * line + pad)};
    bool open = true;
    if (!window(ctx, s, "stats", tr("hud.stats.title"), box, open)) {
        stats_open_ = open;
        return;
    }
    stats_open_ = open;
    float y = box.y + pad + title_h + pad * 0.5f;
    for (const std::string& l : lines) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, l, body, ctx.theme().text);
        y += line;
    }
}

void GameHud::log_window(ui::Context& ctx, GameSession& s) {
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(14.0f);
    const float line = std::round(ctx.text().line_height(small) + ctx.s(6.0f));
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const std::size_t shown = std::min<std::size_t>(notes_.size(), 20);
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(std::min(ctx.s(460.0f), ctx.width() - 2 * pad)),
                 std::round(pad + title_h + pad * 0.5f + static_cast<float>(std::max<std::size_t>(shown, 1)) * line + pad)};
    bool open = true;
    if (!window(ctx, s, "log", tr("hud.log.title"), box, open)) {
        log_open_ = open;
        return;
    }
    log_open_ = open;
    float y = box.y + pad + title_h + pad * 0.5f;
    if (notes_.empty()) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.log.empty"), small, ctx.theme().text_dim);
        return;
    }
    // Newest first; a click goes there.
    for (std::size_t k = 0; k < shown; ++k) {
        const Note& n = notes_[notes_.size() - 1 - k];
        const std::string text = tr("hud.log.row", n.year, n.month, n.day, n.count > 1 ? n.text + " (×" + std::to_string(n.count) + ")" : n.text);
        const ui::Rect r{box.x + pad, y, box.w - 2 * pad, line - ctx.s(2.0f)};
        if (n.has_pos) {
            if (ctx.button(ctx.id("note" + std::to_string(k)), r, text, tr("hud.log.goTo"))) {
                services_.focus_camera(n.x, n.z);
            }
        } else {
            ctx.label(r, text, small, ctx.theme().text);
        }
        y += line;
    }
}

void GameHud::layers_window(ui::Context& ctx, GameSession& s) {
    const float pad = ctx.s(14.0f);
    const float row = std::round(ctx.s(30.0f));
    const float gap = ctx.s(4.0f);
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    static constexpr const char* kLayers[] = {"hud.layers.none",     "hud.layers.fertility", "hud.layers.beauty",
                                              "hud.layers.water",    "hud.layers.market",    "hud.layers.religion",
                                              "hud.layers.health",   "hud.layers.fire",      "hud.layers.routes"};
    ui::Rect box{left_x(ctx), std::round(ctx.s(kTopBarH) + pad), std::round(std::min(ctx.s(300.0f), ctx.width() - 2 * pad)),
                 std::round(pad + title_h + pad * 0.5f + static_cast<float>(std::size(kLayers)) * (row + gap) + pad)};
    bool open = true;
    if (!window(ctx, s, "layers", tr("hud.layers.title"), box, open)) {
        layers_open_ = open;
        return;
    }
    layers_open_ = open;
    float y = box.y + pad + title_h + pad * 0.5f;
    for (std::size_t i = 0; i < std::size(kLayers); ++i) {
        const bool on = services_.overlay() == static_cast<int>(i);
        if (ctx.button(ctx.id(kLayers[i]), {box.x + pad, y, box.w - 2 * pad, row}, tr(kLayers[i]),
                       tr(std::string(kLayers[i]) + ".tooltip"), true, on)) {
            services_.set_overlay(static_cast<int>(i));
        }
        y += row + gap;
    }
}

// --- Notifications ----------------------------------------------------------------------------------

void GameHud::notify(std::string text, bool has_pos, float x, float z, const sim::Calendar& when, std::uint64_t now_ns) {
    if (!notes_.empty()) {
        Note& last = notes_.back();
        if (last.text == text && now_ns - last.at_ns < 10'000'000'000ull) {
            ++last.count;  // The same news again: counted, not repeated.
            last.at_ns = now_ns;
            return;
        }
    }
    Note n;
    n.text = std::move(text);
    n.has_pos = has_pos;
    n.x = x;
    n.z = z;
    n.at_ns = now_ns;
    n.year = static_cast<int>(when.year);
    n.month = static_cast<int>(when.month);
    n.day = static_cast<int>(when.day);
    notes_.push_back(std::move(n));
    if (notes_.size() > 100) {
        notes_.erase(notes_.begin());
    }
}

void GameHud::notifications(ui::Context& ctx, GameSession& s, float bottom) {
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(12.0f);
    const float h = std::round(ctx.text().line_height(small) + ctx.s(12.0f));
    const float w = std::round(std::min(ctx.s(380.0f), ctx.width() * 0.4f));
    const std::uint64_t now = ctx.now_ns();
    float y = bottom - pad - h;
    int drawn = 0;
    for (std::size_t k = notes_.size(); k-- > 0 && drawn < 4;) {
        const Note& n = notes_[k];
        if (now - n.at_ns > kNoteNs) {
            break;
        }
        const ui::Rect r{ctx.width() - pad - w, y, w, h};
        block(s, r);
        const std::string text = n.count > 1 ? n.text + " (×" + std::to_string(n.count) + ")" : n.text;
        if (ctx.button(ctx.id("notification" + std::to_string(k)), r, text,
                       n.has_pos ? tr("hud.log.goTo") : std::string{})) {
            if (n.has_pos) {
                services_.focus_camera(n.x, n.z);
            }
        }
        y -= h + ctx.s(4.0f);
        ++drawn;
    }
}

}  // namespace sc
