// The game windows' frame (section 6.4): moved by the title bar, drawn to
// the screen edges and to each other like magnets, docked in groups that
// move together, collapsed to a tab when they lose the focus and opened
// again under the cursor, pinned to stay open, wider or narrower by the
// corner grip, and remembered in settings.json. Also the launcher on the
// left, the goods, statistics, event log and map layers windows, and the
// notifications.
#include <algorithm>
#include <charconv>
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
constexpr std::uint64_t kCollapseNs = 700'000'000;
constexpr std::uint64_t kNoteNs = 12'000'000'000;

bool inside(const ui::Rect& r, float x, float y) {
    return x >= r.x && y >= r.y && x < r.right() && y < r.bottom();
}

// "id:x,y,w,pinned,group;..." with whole design units.
bool valid_layout_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ':' || c == ',' || c == ';' || c == '-' ||
           c == '_';
}

}  // namespace

void GameHud::load_places() {
    places_loaded_ = true;
    const std::string& text = services_.settings().ui.windows;
    std::size_t at = 0;
    while (at < text.size()) {
        const std::size_t end = std::min(text.find(';', at), text.size());
        const std::string entry = text.substr(at, end - at);
        at = end + 1;
        const std::size_t colon = entry.find(':');
        if (colon == std::string::npos || colon == 0 || colon > 16) {
            continue;
        }
        int values[5] = {0, 0, 0, 0, 0};
        std::size_t p = colon + 1;
        int n = 0;
        for (; n < 5 && p <= entry.size(); ++n) {
            const std::size_t comma = std::min(entry.find(',', p), entry.size());
            const auto r = std::from_chars(entry.data() + p, entry.data() + comma, values[n]);
            if (r.ec != std::errc{} || r.ptr != entry.data() + comma) {
                break;
            }
            p = comma + 1;
        }
        if (n != 5 || values[0] < 0 || values[1] < 0 || values[0] > 20000 || values[1] > 20000 || values[2] < 0 ||
            values[2] > 2000 || values[3] < 0 || values[3] > 1 || values[4] < 0 || values[4] > 1000) {
            continue;  // A damaged entry: that window goes back to its place.
        }
        WindowPlace& w = places_[entry.substr(0, colon)];
        w.x = static_cast<float>(values[0]);
        w.y = static_cast<float>(values[1]);
        w.w = static_cast<float>(values[2]);
        w.placed = true;
        w.pinned = values[3] == 1;
        w.group = values[4];
    }
}

void GameHud::save_places() {
    std::string text;
    for (const auto& [id, w] : places_) {
        if (!w.placed && !w.pinned) {
            continue;
        }
        text += id + ":" + std::to_string(static_cast<int>(std::lround(w.x))) + "," +
                std::to_string(static_cast<int>(std::lround(w.y))) + "," +
                std::to_string(static_cast<int>(std::lround(w.w))) + "," + (w.pinned ? "1" : "0") + "," +
                std::to_string(w.group) + ";";
    }
    if (text.size() > kMaxLayoutBytes || !std::all_of(text.begin(), text.end(), valid_layout_char)) {
        return;
    }
    if (services_.settings().ui.windows != text) {
        services_.settings().ui.windows = text;
        services_.settings_changed();
    }
}

void GameHud::windows_begin(ui::Context& ctx) {
    if (!places_loaded_) {
        load_places();
    }
    shown_last_ = std::move(shown_);
    shown_.clear();
    (void)ctx;
}

void GameHud::windows_end(ui::Context& ctx) {
    const ui::Input& in = ctx.input();
    if (in.mouse_pressed && !ctx.input_blocked()) {
        bool over = false;
        for (const auto& [id, r] : shown_) {
            over = over || inside(r, in.mouse_x, in.mouse_y);
        }
        if (!over) {
            focus_.clear();  // A click on the world or elsewhere.
        }
    }
    if (!in.mouse_down && !dragging_.empty()) {
        dragging_.clear();
        resizing_ = false;
        save_places();
    }
}

bool GameHud::window(ui::Context& ctx, GameSession& s, const std::string& id, const std::string& title, ui::Rect& box,
                     bool& open) {
    WindowPlace& p = places_[id];
    const float sc = ctx.s(1.0f);
    const float pad = ctx.s(14.0f);
    const ui::TextStyle title_style = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float title_h = ctx.text().line_height(title_style);
    const float bar_h = pad + title_h + pad * 0.5f;
    const float button = std::round(ctx.s(34.0f));
    const float min_w = ctx.s(280.0f);
    const ui::Input& in = ctx.input();
    const bool live = !ctx.input_blocked();
    const std::uint64_t now = ctx.now_ns();

    if (p.placed) {
        box.x = std::round(p.x * sc);
        box.y = std::round(p.y * sc);
    } else {
        // Not placed yet: below the windows already at its default place.
        const float step = std::round(title_h + pad * 0.6f) + ctx.s(6.0f);
        for (bool moved = true; moved;) {
            moved = false;
            for (const auto& [other, r] : shown_) {
                if (other != id && std::abs(r.x - box.x) < 4.0f && std::abs(r.y - box.y) < 4.0f) {
                    box.y += std::max(step, r.h + ctx.s(6.0f));
                    moved = true;
                }
            }
        }
        // From now on it stays there (until the player moves it).
        p.x = box.x / sc;
        p.y = box.y / sc;
        p.placed = true;
    }
    if (p.w > 0.0f) {
        box.w = std::round(std::clamp(p.w * sc, min_w, std::max(min_w, ctx.width() - 2 * pad)));
    }
    // Always on the screen, below the top bar.
    box.x = std::clamp(box.x, 0.0f, std::max(0.0f, ctx.width() - box.w));
    box.y = std::clamp(box.y, std::round(ctx.s(kTopBarH)), std::max(std::round(ctx.s(kTopBarH)), ctx.height() - bar_h));

    // Just opened: it takes the focus.
    if (!shown_last_.contains(id) || opened_.contains(id)) {
        focus_ = id;
        seen_ns_[id] = now;
        opened_.erase(id);
    }
    if (inside(box, in.mouse_x, in.mouse_y) || dragging_ == id) {
        seen_ns_[id] = now;
    }
    const bool collapsed = !p.pinned && focus_ != id && dragging_ != id && now - seen_ns_[id] > kCollapseNs;
    if (collapsed) {
        // A tab with the title; the cursor over it opens the window again.
        const float tw = std::min(box.w, ctx.text().measure(ctx.style(ctx.theme().body), title) + 2 * pad + ctx.s(16.0f));
        const ui::Rect tab{box.x, box.y, tw, std::round(title_h + pad * 0.6f)};
        ctx.panel(tab);
        block(s, tab);
        ctx.label(tab.inset(ctx.s(6.0f)), title, ctx.style(ctx.theme().body), ctx.theme().text_dim, ui::Align::Center);
        if (inside(tab, in.mouse_x, in.mouse_y)) {
            seen_ns_[id] = now;
        }
        shown_[id] = tab;
        return false;
    }

    ctx.panel(box);
    block(s, box);
    shown_[id] = box;
    if (live && in.mouse_pressed && inside(box, in.mouse_x, in.mouse_y)) {
        focus_ = id;
    }
    ctx.push_id(id);
    // Title, pin and close.
    const float pin_w = std::round(ctx.s(64.0f));
    ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad - button - pin_w - ctx.s(6.0f), title_h}, title, title_style,
              ctx.theme().accent);
    if (ctx.button(ctx.id("pin"), {box.right() - pad - button - pin_w - ctx.s(6.0f), box.y + pad, pin_w, button},
                   tr(p.pinned ? "hud.window.pinned" : "hud.window.pin"), tr("hud.window.pin.tooltip"), true, p.pinned)) {
        p.pinned = !p.pinned;
        save_places();
    }
    if (ctx.button(ctx.id("close"), {box.right() - pad - button, box.y + pad, button, button}, tr("hud.close"),
                   tr("hud.window.close.tooltip"))) {
        open = false;
    }
    ctx.pop_id();

    // Moving by the title bar (with its group), resizing by the corner.
    const ui::Rect bar{box.x, box.y, box.w - button - pin_w - pad - ctx.s(6.0f), bar_h};
    const ui::Rect grip{box.right() - ctx.s(16.0f), box.bottom() - ctx.s(16.0f), ctx.s(16.0f), ctx.s(16.0f)};
    ctx.draw().rect({grip.x + ctx.s(6.0f), grip.bottom() - ctx.s(4.0f), ctx.s(8.0f), ctx.s(2.0f)}, ctx.theme().panel_border);
    ctx.draw().rect({grip.right() - ctx.s(4.0f), grip.y + ctx.s(6.0f), ctx.s(2.0f), ctx.s(8.0f)}, ctx.theme().panel_border);
    if (live && in.mouse_pressed && dragging_.empty()) {
        if (inside(grip, in.mouse_x, in.mouse_y)) {
            dragging_ = id;
            resizing_ = true;
        } else if (inside(bar, in.mouse_x, in.mouse_y)) {
            dragging_ = id;
            resizing_ = false;
            grab_x_ = in.mouse_x - box.x;
            grab_y_ = in.mouse_y - box.y;
            if ((SDL_GetModState() & SDL_KMOD_CTRL) != 0) {
                p.group = 0;  // Ctrl: out of its group.
            }
        }
    }
    if (dragging_ == id && in.mouse_down) {
        if (resizing_) {
            p.w = std::clamp(in.mouse_x - box.x, min_w, ctx.width()) / sc;
            box.w = std::round(p.w * sc);
            if (!p.placed) {
                p.x = box.x / sc;
                p.y = box.y / sc;
                p.placed = true;
            }
        } else {
            float x = in.mouse_x - grab_x_;
            float y = in.mouse_y - grab_y_;
            // Magnets: the screen edges and the other windows' edges.
            const float snap = kSnap * sc;
            const auto pull = [&](float& v, float target) {
                if (std::abs(v - target) < snap) {
                    v = target;
                }
            };
            pull(x, 0.0f);
            pull(x, ctx.width() - box.w);
            pull(y, std::round(ctx.s(kTopBarH)));
            for (const auto& [other, r] : shown_last_) {
                if (other == id || (p.group != 0 && places_[other].group == p.group)) {
                    continue;
                }
                const bool rows = y < r.bottom() + snap && y + box.h > r.y - snap;
                const bool cols = x < r.right() + snap && x + box.w > r.x - snap;
                if (rows) {
                    pull(x, r.right());
                    pull(x, r.x - box.w);
                    pull(x, r.x);
                }
                if (cols) {
                    pull(y, r.bottom());
                    pull(y, r.y);
                }
            }
            const float dx = x - box.x;
            const float dy = y - box.y;
            box.x = x;
            box.y = y;
            p.x = x / sc;
            p.y = y / sc;
            p.placed = true;
            // The group moves along.
            if (p.group != 0 && (dx != 0.0f || dy != 0.0f)) {
                for (auto& [other, w] : places_) {
                    if (other == id || w.group != p.group) {
                        continue;
                    }
                    if (!w.placed) {
                        const auto it = shown_last_.find(other);
                        if (it == shown_last_.end()) {
                            continue;
                        }
                        w.x = it->second.x / sc;
                        w.y = it->second.y / sc;
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
            if (other == id) {
                continue;
            }
            const bool side = (std::abs(box.x - r.right()) < 1.0f || std::abs(box.right() - r.x) < 1.0f) &&
                              box.y < r.bottom() && box.bottom() > r.y;
            const bool stack = (std::abs(box.y - r.bottom()) < 1.0f || std::abs(box.bottom() - r.y) < 1.0f) &&
                               box.x < r.right() && box.right() > r.x;
            if (side || stack) {
                WindowPlace& o = places_[other];
                if (!o.placed) {
                    o.x = r.x / sc;
                    o.y = r.y / sc;
                    o.placed = true;
                }
                if (o.group == 0) {
                    o.group = next_group_++;
                }
                p.group = o.group;
            }
        }
    }
    return true;
}

void GameHud::open_window(const std::string& id) {
    opened_.insert(id);
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
            *e.open = !*e.open;
            if (*e.open) {
                open_window(e.id);
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
    const std::vector<std::string> lines = {
        tr("hud.stats.population", pop, adults, pop - adults),
        tr("hud.stats.births", ps.births, ps.arrivals),
        tr("hud.stats.deaths", ps.deaths, ps.departures),
        tr("hud.stats.happiness", game.happiness(town)),
        tr("hud.stats.sick", game.sick(town)),
        tr("hud.stats.burned", ps.burned_down),
        tr("hud.stats.raids", ps.raids),
        tr("hud.stats.army", game.soldiers(town), game.military_power(town)),
        tr("hud.stats.coins", ps.coins),
        tr("hud.stats.score", game.score(town)),
        tr("hud.stats.level", game.tier(town)),
    };
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
