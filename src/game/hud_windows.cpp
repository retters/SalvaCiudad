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
#include <utility>

#include <SDL3/SDL_keyboard.h>

#include "game/game_hud.h"
#include "i18n/translator.h"
#include "net/lockstep.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kTopBarH = 52.0f;  // The RmlUi top bar (data/ui/hud/top.rcss) and its margin.
constexpr float kDockW = 76.0f;  // The RmlUi dock (data/ui/hud/dock.rcss) and its margin.
constexpr float kSnap = 12.0f;

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
    bars_last_ = std::move(bars_);
    bars_.clear();
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
    if (!in.mouse_down) {
        tab_pressed_.clear();
    }
}

std::string GameHud::window_title(GameSession& s, const std::string& id) const {
    static constexpr std::pair<const char*, const char*> kFixed[] = {
        {"goods", "hud.goods.title"}, {"stats", "hud.stats.title"},   {"log", "hud.log.title"},
        {"trade", "hud.trade.title"}, {"layers", "hud.layers.title"}, {"army", "hud.army.title"}};
    for (const auto& [name, key] : kFixed) {
        if (id == name) {
            return tr(key);
        }
    }
    if (const WindowList::Object* o = windows_.object(id)) {
        return thing_title(s.game(), o->kind, o->entity);
    }
    if (WindowList::is_camera_id(id) && id.size() == 4 && id[3] >= '1' && id[3] < '1' + kCameraWindows) {
        const auto& cw = s.ui().camera_windows[static_cast<std::size_t>(id[3] - '1')];
        return thing_title(s.game(), static_cast<WindowList::Kind>(cw.kind), cw.entity);
    }
    return id;
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
    // The tabs of its stack go over it (phase 64).
    const std::vector<std::string> tabs = windows_.tabs(id);
    const float tab_h = tabs.empty() ? 0.0f : std::round(ctx.s(26.0f));
    // Always on the screen, below the top bar.
    box.x = std::clamp(box.x, 0.0f, std::max(0.0f, ctx.width() - box.w));
    box.y = std::clamp(box.y, top + tab_h, std::max(top + tab_h, ctx.height() - bar_h));
    if (!tabs.empty()) {
        const ui::TextStyle small = ctx.style(ctx.theme().small);
        const float tab_w = std::floor(std::min(ctx.s(150.0f), box.w / static_cast<float>(tabs.size())));
        ui::Color solid = ctx.theme().panel;
        solid.a = 255;
        for (std::size_t k = 0; k < tabs.size(); ++k) {
            const ui::Rect tab{box.x + static_cast<float>(k) * tab_w, box.y - tab_h, tab_w, tab_h};
            const bool mine = tabs[k] == id;
            ctx.draw().rect(tab, mine ? solid : ctx.theme().button_active);
            ctx.draw().rect_outline(tab, ctx.theme().panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
            ctx.label(tab.inset(ctx.s(4.0f)), window_title(s, tabs[k]), small, mine ? ctx.theme().accent : ctx.theme().text_dim,
                      ui::Align::Center);
            block(s, tab);
            if (live && in.mouse_pressed && inside(tab, in.mouse_x, in.mouse_y)) {
                // A click shows it; holding and moving away pulls it out.
                tab_pressed_ = tabs[k];
                tab_press_x_ = in.mouse_x;
                tab_press_y_ = in.mouse_y;
                if (!mine) {
                    windows_.raise(tabs[k]);
                }
            }
        }
        if (!tab_pressed_.empty() && in.mouse_down && dragging_.empty() &&
            std::find(tabs.begin(), tabs.end(), tab_pressed_) != tabs.end() &&
            std::abs(in.mouse_x - tab_press_x_) + std::abs(in.mouse_y - tab_press_y_) > ctx.s(10.0f)) {
            // Out of the stack, under the cursor, and dragged from now on.
            windows_.split(tab_pressed_);
            WindowList::Place& out = windows_.place(tab_pressed_);
            grab_x_ = ctx.s(60.0f);
            grab_y_ = bar_h * 0.5f;
            out.x = (in.mouse_x - grab_x_) / sc;
            out.y = (in.mouse_y - grab_y_) / sc;
            out.placed = true;
            windows_.raise(tab_pressed_);
            dragging_ = tab_pressed_;
            resizing_ = false;
            tab_pressed_.clear();
        }
    }

    // Solid: what lies behind a window does not show through it.
    ui::Color solid = ctx.theme().panel;
    solid.a = 255;
    ctx.draw().rect(box, solid);
    ctx.panel(box);
    block(s, box);
    shown_[id] = {box.x, box.y - tab_h, box.w, box.h + tab_h};
    bars_[id] = {box.x, box.y - tab_h, box.w, tab_h + bar_h};
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
    // Released over another window's title: they become tabs of one window.
    bool merged = false;
    if (dragging_ == id && !in.mouse_down && !resizing_) {
        std::string onto;
        const std::vector<std::string> mine = windows_.tabs(id);
        for (const std::string& other : windows_.order()) {  // The one in front wins.
            const auto bar_it = bars_last_.find(other);
            if (other != id && bar_it != bars_last_.end() && inside(bar_it->second, in.mouse_x, in.mouse_y) &&
                std::find(mine.begin(), mine.end(), other) == mine.end()) {
                onto = other;
            }
        }
        if (!onto.empty()) {
            windows_.merge(id, onto);
            merged = true;
        }
    }
    // Released touching another window: they dock.
    if (dragging_ == id && !in.mouse_down && !resizing_ && !merged) {
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
    if (!merged) {
        windows_.sync_stack(id);  // Its tabs stay where it is.
    }
    return !closed && !windows_.place(id).minimized;
}

void GameHud::open_window(const std::string& id) {
    windows_.raise(id);
}

float GameHud::left_x(ui::Context& ctx) const {
    return std::round(ctx.s(kDockW + 8.0f));
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

}  // namespace sc
