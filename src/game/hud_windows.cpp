// The game windows (section 6.4, phase 62): where they are, kept in
// settings.json (game/window_list.h keeps the list), their titles, and the
// notifications. Since phase 127 the frame is RmlUi's (hud_rml_windows.cpp).
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
    hover_top_ = windows_.top_at(shown_last_, in.mouse_x, in.mouse_y);
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
