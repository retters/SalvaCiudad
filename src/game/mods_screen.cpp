#include "game/mods_screen.h"

#include <algorithm>
#include <cmath>
#include <format>

#include "i18n/translator.h"
#include "mods/mod_library.h"

namespace sc {

using i18n::tr;

void ModsScreen::open() {
    enabled_ = services_.mod_library().enabled_ids();
    dirty_ = false;
}

bool ModsScreen::frame(ui::Context& ctx, bool input_blocked) {
    ctx.set_input_blocked(input_blocked);
    mods::ModLibrary& library = services_.mod_library();
    const float margin = ctx.s(16.0f);
    const float panel_w = std::min(ctx.s(900.0f), ctx.width() - 2 * margin);
    const ui::Rect panel{std::round((ctx.width() - panel_w) * 0.5f), margin, std::round(panel_w), ctx.height() - 2 * margin};
    ctx.panel(panel);
    const float pad = ctx.s(20.0f);
    const float x = panel.x + pad;
    const float w = panel.w - 2 * pad;
    const ui::TextStyle title_st = ctx.style(ctx.theme().title, ui::FontRole::Bold);
    const ui::TextStyle bold = ctx.style(ctx.theme().body, ui::FontRole::Bold);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float title_h = ctx.text().line_height(title_st);
    float y = panel.y + pad;
    ctx.label({x, y, w, title_h}, tr("mods.title"), title_st, ctx.theme().accent);
    y += title_h + ctx.s(6.0f);
    const float hint_h = ctx.paragraph({x, y, w, 0}, tr("mods.hint"), small, ctx.theme().text_dim);
    y += hint_h + ctx.s(12.0f);

    const float bar_h = ctx.s(44.0f);
    const float bar_y = panel.bottom() - pad - bar_h;
    const ui::Rect list_area{x, y, w, std::max(0.0f, bar_y - ctx.s(12.0f) - y)};
    float cy = ctx.begin_scroll(ctx.id("mods_list"), list_area);
    const float top = cy;
    const float row_gap = ctx.s(10.0f);
    const float check = ctx.s(30.0f);
    const float small_button = ctx.s(40.0f);

    // Enabled mods in their order first, then the others by name.
    std::vector<const mods::ModInfo*> rows;
    if (const mods::ModInfo* core = library.find(mods::kCoreModId)) {
        rows.push_back(core);
    }
    for (const std::string& id : enabled_) {
        if (const mods::ModInfo* m = library.find(id)) {
            rows.push_back(m);
        }
    }
    for (const mods::ModInfo& m : library.mods()) {
        if (std::find(rows.begin(), rows.end(), &m) == rows.end()) {
            rows.push_back(&m);
        }
    }
    std::string toggle;
    std::string up;
    std::string down;
    for (const mods::ModInfo* m : rows) {
        const std::string& id = m->manifest.id;
        const bool core = id == mods::kCoreModId;
        const bool on = core || std::find(enabled_.begin(), enabled_.end(), id) != enabled_.end();
        const bool usable = m->errors.empty();
        std::string name = tr(m->manifest.name_key);
        if (name == m->manifest.name_key || name.empty()) {
            name = id;  // Its texts are only loaded while the mod is on.
        }
        const std::string details =
            tr("mods.details", mods::version_text(m->manifest.version),
               m->manifest.authors.empty() ? std::string("-") : m->manifest.authors.front(),
               tr(m->builtin ? "mods.builtin" : "mods.user"), std::format("{:016x}", m->hash));
        std::string status;
        ui::Color status_color = ctx.theme().text_dim;
        if (!m->errors.empty()) {
            status = tr("mods.status.errors");
            for (const std::string& e : m->errors) {
                status += "\n- " + e;
            }
            status_color = ctx.theme().danger;
        } else if (on && !m->loaded) {
            status = tr("mods.status.pending");
        } else if (m->loaded) {
            status = tr(m->manifest.affects_simulation ? "mods.status.loaded" : "mods.status.loadedVisual");
        } else {
            status = tr("mods.status.off");
        }
        const float text_x = x + check + ctx.s(12.0f);
        const float text_w = w - (text_x - x) - 2 * small_button - ctx.s(16.0f);
        const float name_h = ctx.text().line_height(bold);
        const float details_h = ctx.paragraph_height(text_w, details, small);
        const float status_h = ctx.paragraph_height(text_w, status, small);
        const float row_h = std::max(check, name_h + details_h + status_h + ctx.s(8.0f));
        ctx.push_id(id);
        bool value = on;
        if (ctx.checkbox(ctx.id("on"), {x, cy, check, check}, value, tr(core ? "mods.coreAlways" : "mods.toggle.tooltip"),
                         !core && (usable || on))) {
            toggle = id;
        }
        ctx.label({text_x, cy, text_w, name_h}, name, bold, ctx.theme().text);
        float ty = cy + name_h;
        ty += ctx.paragraph({text_x, ty, text_w, 0}, details, small, ctx.theme().text_dim);
        (void)ctx.paragraph({text_x, ty + ctx.s(4.0f), text_w, 0}, status, small, status_color);
        if (on && !core) {
            const float bx = x + w - 2 * small_button - ctx.s(8.0f);
            if (ctx.button(ctx.id("up"), {bx, cy, small_button, small_button}, "^", tr("mods.up.tooltip"))) {
                up = id;
            }
            if (ctx.button(ctx.id("down"), {bx + small_button + ctx.s(8.0f), cy, small_button, small_button}, "v",
                           tr("mods.down.tooltip"))) {
                down = id;
            }
        }
        ctx.pop_id();
        cy += row_h + row_gap;
        ctx.draw().rect({x, cy - row_gap * 0.5f, w, std::max(1.0f, std::round(ctx.s(1.0f)))},
                        ctx.theme().panel_border.with_alpha(0.4f));
    }
    ctx.end_scroll(cy - top);

    if (!toggle.empty()) {
        const auto it = std::find(enabled_.begin(), enabled_.end(), toggle);
        if (it != enabled_.end()) {
            enabled_.erase(it);
        } else {
            enabled_.push_back(toggle);
        }
        dirty_ = true;
    }
    for (const auto& [id, delta] : {std::pair<std::string, int>{up, -1}, {down, 1}}) {
        const auto it = std::find(enabled_.begin(), enabled_.end(), id);
        if (id.empty() || it == enabled_.end()) {
            continue;
        }
        const auto pos = static_cast<int>(it - enabled_.begin());
        const int to = std::clamp(pos + delta, 0, static_cast<int>(enabled_.size()) - 1);
        std::swap(enabled_[static_cast<std::size_t>(pos)], enabled_[static_cast<std::size_t>(to)]);
        dirty_ = true;
    }

    // Bottom bar.
    const float gap = ctx.s(12.0f);
    const float bw = std::min(ctx.s(210.0f), (w - 2 * gap) / 3.0f);
    const ui::Rect apply{x + w - bw, bar_y, bw, bar_h};
    const ui::Rect folder{apply.x - gap - bw, bar_y, bw, bar_h};
    const ui::Rect back{x, bar_y, bw, bar_h};
    bool stay = true;
    if (ctx.button(ctx.id("mods_back"), back, tr("mods.back"), tr("mods.back.tooltip")) ||
        (!input_blocked && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        stay = false;
    }
    if (ctx.button(ctx.id("mods_folder"), folder, tr("mods.openFolder"), tr("mods.openFolder.tooltip"))) {
        services_.open_mods_folder();
    }
    if (ctx.button(ctx.id("mods_apply"), apply, tr("mods.apply"), tr("mods.apply.tooltip"), true, dirty_)) {
        services_.apply_mods(enabled_);
        enabled_ = library.enabled_ids();
        dirty_ = false;
    }
    return stay;
}

}  // namespace sc
