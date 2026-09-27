#include "game/settings_screen.h"

#include <algorithm>
#include <cmath>
#include <string>

#include "game/ui_host.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kRowHeight = 40.0f;
constexpr float kRowGap = 10.0f;
constexpr float kWideLayout = 620.0f;  // Below this width, labels go above controls.

constexpr int kFpsOptions[] = {0, 30, 60, 90, 120, 144, 165, 240};
// 0 is "automatic", the same as 100 % of the screen scale (decision D-207).
constexpr double kScaleOptions[] = {0.0, 0.75, 0.9, 1.1, 1.25, 1.5, 1.75, 2.0};
constexpr int kAutosaveOptions[] = {0, 5, 10, 15, 30, 60};

std::string percent(int v) {
    return tr("settings.value.percent", v);
}

// Four-level options ("off/low/medium/high" and similar) from text keys.
std::vector<std::string> level_options(const char* base) {
    std::vector<std::string> out;
    for (int i = 0; i < 4; ++i) {
        out.push_back(tr(std::string(base) + "." + std::to_string(i)));
    }
    return out;
}

// Index of the option closest to `value`.
template <typename T, std::size_t N>
int closest_index(const T (&options)[N], T value) {
    int best = 0;
    for (std::size_t i = 0; i < N; ++i) {
        if (std::abs(static_cast<double>(options[i] - value)) <
            std::abs(static_cast<double>(options[static_cast<std::size_t>(best)] - value))) {
            best = static_cast<int>(i);
        }
    }
    return best;
}

}  // namespace

SettingsScreen::Row SettingsScreen::row(ui::Context& ctx, float x, float& y, float width, std::string_view label,
                                        std::string_view tooltip) {
    const float h = ctx.s(kRowHeight);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    Row r;
    if (width >= ctx.s(kWideLayout)) {
        const float label_w = std::round(width * 0.42f);
        r.label = {x, y, label_w - ctx.s(12.0f), h};
        r.control = {x + label_w, y, width - label_w, h};
        y += h + ctx.s(kRowGap);
    } else {
        const float lh = ctx.text().line_height(st);
        r.label = {x, y, width, lh};
        r.control = {x, y + lh + ctx.s(4.0f), width, h};
        y += lh + ctx.s(4.0f) + h + ctx.s(kRowGap);
    }
    ctx.tooltip_area(ctx.id(std::string(label) + "#row"), {x, r.label.y, width, r.control.bottom() - r.label.y}, tooltip);
    ctx.label(r.label, label, st, ctx.theme().text);
    return r;
}

void SettingsScreen::section(ui::Context& ctx, float x, float& y, float width, std::string_view title) {
    const ui::TextStyle st = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float h = ctx.text().line_height(st);
    y += ctx.s(6.0f);
    ctx.label({x, y, width, h}, title, st, ctx.theme().accent);
    y += h;
    ctx.draw().rect({x, y, width, std::max(1.0f, std::round(ctx.s(1.0f)))}, ctx.theme().panel_border);
    y += ctx.s(12.0f);
}

bool SettingsScreen::frame(ui::Context& ctx, UiHost& host, bool input_blocked) {
    const bool blocked = input_blocked || capture_.has_value();
    ctx.set_input_blocked(blocked);
    bool stay = true;

    const float margin = ctx.s(16.0f);
    const float panel_w = std::min(ctx.s(1000.0f), ctx.width() - 2 * margin);
    const ui::Rect panel{std::round((ctx.width() - panel_w) * 0.5f), margin, std::round(panel_w),
                         ctx.height() - 2 * margin};
    ctx.panel(panel);
    const float pad = ctx.s(20.0f);
    const float inner_x = panel.x + pad;
    const float inner_w = panel.w - 2 * pad;
    static constexpr const char* kTabKeys[] = {"display", "graphics", "audio", "controls", "interface", "language", "game"};
    const ui::TextStyle title_st = ctx.style(ctx.theme().title, ui::FontRole::Bold);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float title_h = ctx.text().line_height(title_st);
    const float tab_h = ctx.s(38.0f);
    const float tab_gap = ctx.s(6.0f);

    // Title and tabs; the tabs flow onto several lines when they do not fit.
    // Returns the header height; draws only when `draw` is set.
    const auto header = [&](float top, bool draw) {
        float y = top;
        if (draw) {
            ctx.label({inner_x, y, inner_w, title_h}, tr("settings.title"), title_st, ctx.theme().accent);
        }
        y += title_h + ctx.s(10.0f);
        float tx = inner_x;
        for (std::size_t i = 0; i < std::size(kTabKeys); ++i) {
            const std::string label = tr(std::string("settings.tab.") + kTabKeys[i]);
            const float tw = std::min(inner_w, ctx.text().measure(body, label) + ctx.s(32.0f));
            if (tx + tw > inner_x + inner_w + 0.5f) {
                tx = inner_x;
                y += tab_h + tab_gap;
            }
            if (draw) {
                const bool selected = static_cast<std::size_t>(tab_) == i;
                if (ctx.button(ctx.id(std::string("tab_") + kTabKeys[i]), {tx, y, tw, tab_h}, label, {}, true, selected)) {
                    tab_ = static_cast<Tab>(i);
                }
                if (selected) {
                    ctx.draw().rect({tx, y + tab_h - ctx.s(3.0f), tw, ctx.s(3.0f)}, ctx.theme().accent);
                }
            }
            tx += tw + tab_gap;
        }
        return y + tab_h + ctx.s(14.0f) - top;
    };

    // Bottom bar, always visible.
    const float bar_h = ctx.s(44.0f);
    const float bar_y = panel.bottom() - pad - bar_h;
    const float top = panel.y + pad;
    const float header_h = header(top, false);
    const float area_h = std::max(0.0f, bar_y - ctx.s(12.0f) - top);
    // When the window is small for the interface size, the header scrolls
    // with the options instead of leaving them no room.
    const bool header_fixed = area_h - header_h >= area_h * 0.45f;
    if (header_fixed) {
        (void)header(top, true);
    }
    const float view_top = header_fixed ? top + header_h : top;
    const ui::Rect viewport{inner_x, view_top, inner_w, std::max(0.0f, bar_y - ctx.s(12.0f) - view_top)};

    const float content_top = ctx.begin_scroll(ctx.id(std::string("tab_scroll_") + kTabKeys[static_cast<std::size_t>(tab_)]), viewport);
    float cy = content_top;
    if (!header_fixed) {
        cy += header(cy, true);
    }
    const float cw = inner_w - ctx.s(14.0f);  // Room for the scroll bar.
    ctx.push_id(kTabKeys[static_cast<std::size_t>(tab_)]);
    switch (tab_) {
        case Tab::Display: tab_display(ctx, host, inner_x, cy, cw); break;
        case Tab::Graphics: tab_graphics(ctx, inner_x, cy, cw); break;
        case Tab::Audio: tab_audio(ctx, inner_x, cy, cw); break;
        case Tab::Controls: tab_controls(ctx, inner_x, cy, cw); break;
        case Tab::Interface: tab_interface(ctx, inner_x, cy, cw); break;
        case Tab::Language: tab_language(ctx, inner_x, cy, cw); break;
        case Tab::Game: tab_game(ctx, inner_x, cy, cw); break;
        case Tab::Count: break;
    }
    ctx.pop_id();
    ctx.end_scroll(cy - content_top);

    const float gap = ctx.s(12.0f);
    const float back_w = std::min(ctx.s(200.0f), (inner_w - gap) * 0.4f);
    const ui::Rect back{inner_x + inner_w - back_w, bar_y, back_w, bar_h};
    const ui::Rect restore{inner_x, bar_y, std::min(ctx.s(360.0f), inner_w - back_w - gap), bar_h};
    if (ctx.button(ctx.id("restore"), restore, tr("settings.restoreDefaults"), tr("settings.restoreDefaults.tooltip"))) {
        restore_tab_defaults(host);
    }
    if (ctx.button(ctx.id("back"), back, tr("settings.back"), {}, true, true) ||
        (!blocked && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        stay = false;
    }

    if (capture_) {
        ctx.set_input_blocked(input_blocked);
        capture_dialog(ctx);
        handle_key_capture(ctx);
    }
    return stay;
}

void SettingsScreen::tab_display(ui::Context& ctx, UiHost& host, float x, float& y, float w) {
    Settings& s = services_.settings();
    DisplaySettings d = s.display;

    // Mode.
    {
        const WindowMode modes[] = {WindowMode::Fullscreen, WindowMode::Borderless, WindowMode::Windowed};
        const std::vector<std::string> options = {tr("settings.display.mode.fullscreen"),
                                                  tr("settings.display.mode.borderless"),
                                                  tr("settings.display.mode.windowed")};
        int index = static_cast<int>(std::find(std::begin(modes), std::end(modes), d.mode) - std::begin(modes));
        const Row r = row(ctx, x, y, w, tr("settings.display.mode"), tr("settings.display.mode.tooltip"));
        if (ctx.selector(ctx.id("mode"), r.control, index, options, tr("settings.display.mode.tooltip"))) {
            d.mode = modes[static_cast<std::size_t>(index)];
            host.change_display(d);
        }
    }
    // Monitor.
    {
        const std::vector<std::string> monitors = services_.monitor_names();
        std::vector<std::string> options = {tr("settings.display.monitor.primary")};
        options.insert(options.end(), monitors.begin(), monitors.end());
        int index = 0;
        for (std::size_t i = 0; i < monitors.size(); ++i) {
            if (monitors[i] == d.monitor) {
                index = static_cast<int>(i) + 1;
            }
        }
        const Row r = row(ctx, x, y, w, tr("settings.display.monitor"), tr("settings.display.monitor.tooltip"));
        if (ctx.selector(ctx.id("monitor"), r.control, index, options, tr("settings.display.monitor.tooltip"))) {
            d.monitor = index == 0 ? std::string{} : monitors[static_cast<std::size_t>(index - 1)];
            host.change_display(d);
        }
    }
    // Resolution (exclusive fullscreen only).
    {
        const std::vector<Resolution> modes = services_.fullscreen_resolutions(d.monitor);
        std::vector<std::string> options = {tr("settings.display.resolution.desktop")};
        int index = 0;
        for (std::size_t i = 0; i < modes.size(); ++i) {
            options.push_back(tr("settings.display.resolution.value", std::to_string(modes[i].width),
                                 std::to_string(modes[i].height)));
            if (modes[i].width == d.fullscreen_width && modes[i].height == d.fullscreen_height) {
                index = static_cast<int>(i) + 1;
            }
        }
        const bool enabled = d.mode == WindowMode::Fullscreen;
        const std::string tip = tr(enabled ? "settings.display.resolution.tooltip"
                                           : "settings.display.resolution.disabledTooltip");
        const Row r = row(ctx, x, y, w, tr("settings.display.resolution"), tip);
        if (ctx.selector(ctx.id("resolution"), r.control, index, options, tip, enabled)) {
            d.fullscreen_width = index == 0 ? 0 : modes[static_cast<std::size_t>(index - 1)].width;
            d.fullscreen_height = index == 0 ? 0 : modes[static_cast<std::size_t>(index - 1)].height;
            host.change_display(d);
        }
    }
    // VSync and frame limit apply at once; they cannot break the display.
    {
        const Row r = row(ctx, x, y, w, tr("settings.display.vsync"), tr("settings.display.vsync.tooltip"));
        if (ctx.checkbox(ctx.id("vsync"), r.control, s.display.vsync, tr("settings.display.vsync.tooltip"))) {
            services_.apply_vsync();
            services_.settings_changed();
        }
    }
    {
        std::vector<std::string> options;
        for (const int fps : kFpsOptions) {
            options.push_back(fps == 0 ? tr("settings.display.fpsLimit.none") : tr("settings.display.fpsLimit.value", fps));
        }
        int index = closest_index(kFpsOptions, s.display.fps_limit);
        const bool enabled = !s.display.vsync;
        const std::string tip = tr(enabled ? "settings.display.fpsLimit.tooltip" : "settings.display.fpsLimit.disabledTooltip");
        const Row r = row(ctx, x, y, w, tr("settings.display.fpsLimit"), tip);
        if (ctx.selector(ctx.id("fps"), r.control, index, options, tip, enabled)) {
            s.display.fps_limit = kFpsOptions[static_cast<std::size_t>(index)];
            services_.settings_changed();
        }
    }
}

void SettingsScreen::tab_graphics(ui::Context& ctx, float x, float& y, float w) {
    GraphicsSettings& g = services_.settings().graphics;

    bool changed = false;
    {
        const std::vector<std::string> options = {tr("settings.graphics.preset.low"), tr("settings.graphics.preset.medium"),
                                                  tr("settings.graphics.preset.high"), tr("settings.graphics.preset.ultra"),
                                                  tr("settings.graphics.preset.custom")};
        int index = static_cast<int>(g.preset);
        const Row r = row(ctx, x, y, w, tr("settings.graphics.preset"), tr("settings.graphics.preset.tooltip"));
        if (ctx.selector(ctx.id("preset"), r.control, index, options, tr("settings.graphics.preset.tooltip"))) {
            const auto p = static_cast<QualityPreset>(index);
            if (p != QualityPreset::Custom) {
                g.apply_preset(p);
            }
            changed = true;
        }
    }
    struct Level {
        const char* key;
        int* value;
    };
    const Level levels[] = {{"shadows", &g.shadows}, {"drawDistance", &g.draw_distance},
                            {"vegetation", &g.vegetation}, {"antialiasing", &g.antialiasing}};
    for (const Level& l : levels) {
        const std::string base = std::string("settings.graphics.") + l.key;
        const std::vector<std::string> options = level_options((base + ".level").c_str());
        const Row r = row(ctx, x, y, w, tr(base), tr(base + ".tooltip"));
        if (ctx.selector(ctx.id(l.key), r.control, *l.value, options, tr(base + ".tooltip"))) {
            changed = true;
        }
    }
    if (changed) {
        g.preset = g.matching_preset();
        services_.apply_graphics();
        services_.settings_changed();
    }
}

void SettingsScreen::tab_audio(ui::Context& ctx, float x, float& y, float w) {
    AudioSettings& a = services_.settings().audio;
    const float note_h = ctx.paragraph({x, y, w, 0}, tr("settings.audio.pendingNote"), ctx.style(ctx.theme().small),
                                       ctx.theme().text_dim);
    y += note_h + ctx.s(12.0f);
    struct Volume {
        const char* key;
        int* value;
    };
    const Volume volumes[] = {{"master", &a.master}, {"effects", &a.effects}, {"ambient", &a.ambient},
                              {"music", &a.music}, {"ui", &a.ui}};
    for (const Volume& v : volumes) {
        const std::string base = std::string("settings.audio.") + v.key;
        const Row r = row(ctx, x, y, w, tr(base), tr(base + ".tooltip"));
        if (ctx.slider(ctx.id(v.key), r.control, *v.value, 0, 100, 5, percent, tr(base + ".tooltip"))) {
            services_.settings_changed();
        }
    }
}

void SettingsScreen::tab_controls(ui::Context& ctx, float x, float& y, float w) {
    InputSettings& in = services_.settings().input;
    section(ctx, x, y, w, tr("settings.controls.camera"));
    struct Speed {
        const char* key;
        double* value;
    };
    const Speed speeds[] = {{"panSpeed", &in.camera_pan_speed}, {"rotateSpeed", &in.camera_rotate_speed},
                            {"zoomSpeed", &in.camera_zoom_speed}};
    for (const Speed& sp : speeds) {
        const std::string base = std::string("settings.controls.") + sp.key;
        int pct = static_cast<int>(std::lround(*sp.value * 100.0));
        const Row r = row(ctx, x, y, w, tr(base), tr(base + ".tooltip"));
        if (ctx.slider(ctx.id(sp.key), r.control, pct, 25, 400, 5, percent, tr(base + ".tooltip"))) {
            *sp.value = static_cast<double>(pct) / 100.0;
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.controls.invertZoom"), tr("settings.controls.invertZoom.tooltip"));
        if (ctx.checkbox(ctx.id("invertZoom"), r.control, in.invert_zoom, tr("settings.controls.invertZoom.tooltip"))) {
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.controls.edgeScroll"), tr("settings.controls.edgeScroll.tooltip"));
        if (ctx.checkbox(ctx.id("edgeScroll"), r.control, in.edge_scroll, tr("settings.controls.edgeScroll.tooltip"))) {
            services_.settings_changed();
        }
    }

    if (!binding_notice_.empty()) {
        y += ctx.s(6.0f);
        y += ctx.paragraph({x, y, w, 0}, binding_notice_, ctx.style(ctx.theme().body), ctx.theme().accent);
    }

    const ActionGroup groups[] = {ActionGroup::Camera, ActionGroup::Game, ActionGroup::Interface};
    const char* group_keys[] = {"settings.controls.group.camera", "settings.controls.group.game",
                                "settings.controls.group.interface"};
    for (std::size_t gi = 0; gi < std::size(groups); ++gi) {
        section(ctx, x, y, w, tr(group_keys[gi]));
        for (const ActionInfo& info : action_table()) {
            if (info.group != groups[gi]) {
                continue;
            }
            const std::string name = tr("action." + std::string(info.id));
            const std::string tip = tr("settings.controls.binding.tooltip", name);
            const Row r = row(ctx, x, y, w, name, tip);
            const float gap = ctx.s(8.0f);
            const float bw = (r.control.w - gap) * 0.5f;
            for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
                const SDL_Scancode key = in.bindings.key(info.action, slot);
                const std::string label = key == SDL_SCANCODE_UNKNOWN ? tr("settings.controls.unbound") : key_display_name(key);
                const ui::Rect b{r.control.x + static_cast<float>(slot) * (bw + gap), r.control.y, bw, r.control.h};
                const bool active = capture_ && capture_->action == info.action && capture_->slot == slot;
                if (ctx.button(ctx.id(std::string(info.id) + "#" + std::to_string(slot)), b, label, tip, true, active)) {
                    capture_ = Capture{info.action, slot};
                    binding_notice_.clear();
                }
            }
        }
    }
}

void SettingsScreen::capture_dialog(ui::Context& ctx) {
    const std::string action = tr("action." + std::string(action_info(capture_->action).id));
    const std::string text = tr("settings.controls.capture", action);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(520.0f), ctx.width() - ctx.s(32.0f));
    const float pad = ctx.s(24.0f);
    const float h = ctx.paragraph_height(w - 2 * pad, text, body) + 2 * pad;
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round((ctx.height() - h) * 0.5f), w, h};
    ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().overlay);
    ctx.panel(box);
    ctx.paragraph(box.inset(pad), text, body, ctx.theme().text, ui::Align::Center);
}

void SettingsScreen::handle_key_capture(ui::Context& ctx) {
    if (!capture_ || ctx.input().keys.empty()) {
        return;
    }
    const SDL_Scancode key = ctx.input().keys.front();
    KeyBindings& bindings = services_.settings().input.bindings;
    const Capture c = *capture_;
    capture_.reset();
    if (key == SDL_SCANCODE_ESCAPE) {
        return;
    }
    if (key == SDL_SCANCODE_DELETE || key == SDL_SCANCODE_BACKSPACE) {
        bindings.set_key(c.action, c.slot, SDL_SCANCODE_UNKNOWN);
        services_.settings_changed();
        return;
    }
    // A key belongs to one action only: take it from the other one.
    Action other{};
    std::size_t other_slot = 0;
    if (bindings.find(key, other, other_slot) && (other != c.action || other_slot != c.slot)) {
        bindings.set_key(other, other_slot, SDL_SCANCODE_UNKNOWN);
        binding_notice_ = tr("settings.controls.moved", key_display_name(key),
                             tr("action." + std::string(action_info(other).id)));
    }
    bindings.set_key(c.action, c.slot, key);
    services_.settings_changed();
}

void SettingsScreen::tab_interface(ui::Context& ctx, float x, float& y, float w) {
    Settings& s = services_.settings();
    {
        std::vector<std::string> options;
        for (const double scale : kScaleOptions) {
            options.push_back(scale == 0.0 ? tr("settings.interface.scale.auto")
                                           : percent(static_cast<int>(std::lround(scale * 100.0))));
        }
        int index = s.display.ui_scale == 1.0 ? 0 : closest_index(kScaleOptions, s.display.ui_scale);
        const Row r = row(ctx, x, y, w, tr("settings.interface.scale"), tr("settings.interface.scale.tooltip"));
        if (ctx.selector(ctx.id("scale"), r.control, index, options, tr("settings.interface.scale.tooltip"))) {
            s.display.ui_scale = kScaleOptions[static_cast<std::size_t>(index)];
            services_.settings_changed();
        }
    }
    {
        const auto& families = services_.fonts().ui_families();
        std::vector<std::string> options;
        int index = 0;
        for (std::size_t i = 0; i < families.size(); ++i) {
            options.push_back(families[i].name);
            if (families[i].id == s.ui.font) {
                index = static_cast<int>(i);
            }
        }
        const Row r = row(ctx, x, y, w, tr("settings.interface.font"), tr("settings.interface.font.tooltip"));
        if (ctx.selector(ctx.id("font"), r.control, index, options, tr("settings.interface.font.tooltip"))) {
            s.ui.font = families[static_cast<std::size_t>(index)].id;
            services_.apply_font();
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.interface.tooltips"), tr("settings.interface.tooltips.tooltip"));
        if (ctx.checkbox(ctx.id("tooltips"), r.control, s.ui.show_tooltips, tr("settings.interface.tooltips.tooltip"))) {
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.interface.tooltipDelay"), tr("settings.interface.tooltipDelay.tooltip"));
        if (ctx.slider(ctx.id("tooltipDelay"), r.control, s.ui.tooltip_delay_ms, 0, settings_limits::kMaxTooltipDelayMs,
                       100, [](int v) { return tr("settings.value.ms", v); }, tr("settings.interface.tooltipDelay.tooltip"),
                       s.ui.show_tooltips)) {
            services_.settings_changed();
        }
    }
}

void SettingsScreen::tab_language(ui::Context& ctx, float x, float& y, float w) {
    Settings& s = services_.settings();
    const auto languages = i18n::translator().available();
    const float h = ctx.s(kRowHeight);
    const float gap = ctx.s(8.0f);
    const float bw = std::min(w, ctx.s(420.0f));

    const bool is_auto = s.language == "auto";
    if (ctx.button(ctx.id("auto"), {x, y, bw, h}, tr("settings.language.auto"), tr("settings.language.auto.tooltip"), true,
                   is_auto)) {
        s.language = "auto";
        services_.apply_language();
        services_.settings_changed();
    }
    y += h + gap;
    for (const i18n::LanguageInfo* lang : languages) {
        const bool selected = !is_auto && s.language == lang->code;
        if (ctx.button(ctx.id(lang->code), {x, y, bw, h}, lang->native_name, {}, true, selected)) {
            s.language = lang->code;
            services_.apply_language();
            services_.settings_changed();
        }
        y += h + gap;
    }
    y += ctx.s(8.0f);
    y += ctx.paragraph({x, y, w, 0}, tr("settings.language.addHint"), ctx.style(ctx.theme().small), ctx.theme().text_dim);
}

void SettingsScreen::tab_game(ui::Context& ctx, float x, float& y, float w) {
    GameplaySettings& g = services_.settings().gameplay;
    {
        std::vector<std::string> options;
        for (const int minutes : kAutosaveOptions) {
            options.push_back(minutes == 0 ? tr("settings.game.autosave.off") : i18n::tr_n("settings.game.autosave.minutes", minutes));
        }
        int index = closest_index(kAutosaveOptions, g.autosave_minutes);
        const Row r = row(ctx, x, y, w, tr("settings.game.autosave"), tr("settings.game.autosave.tooltip"));
        if (ctx.selector(ctx.id("autosave"), r.control, index, options, tr("settings.game.autosave.tooltip"))) {
            g.autosave_minutes = kAutosaveOptions[static_cast<std::size_t>(index)];
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.game.autosaveKeep"), tr("settings.game.autosaveKeep.tooltip"));
        if (ctx.slider(ctx.id("autosaveKeep"), r.control, g.autosave_keep, 1, settings_limits::kMaxAutosaveKeep, 1,
                       [](int v) { return i18n::tr_n("settings.game.autosaveKeep.value", v); },
                       tr("settings.game.autosaveKeep.tooltip"), g.autosave_minutes > 0)) {
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.game.tutorial"), tr("settings.game.tutorial.tooltip"));
        if (ctx.button(ctx.id("tutorial"), r.control, tr("settings.game.tutorial.button"), tr("settings.game.tutorial.tooltip"),
                       g.tutorial_seen)) {
            g.tutorial_seen = false;
            services_.settings_changed();
        }
    }
    {
        const Row r = row(ctx, x, y, w, tr("settings.game.dataFolder"), tr("settings.game.dataFolder.tooltip"));
        if (ctx.button(ctx.id("dataFolder"), r.control, tr("settings.game.dataFolder.button"),
                       tr("settings.game.dataFolder.tooltip"))) {
            services_.open_data_folder();
        }
    }
}

void SettingsScreen::restore_tab_defaults(UiHost& host) {
    Settings& s = services_.settings();
    const Settings defaults;
    switch (tab_) {
        case Tab::Display: {
            DisplaySettings d = s.display;
            d.mode = defaults.display.mode;
            d.monitor = defaults.display.monitor;
            d.fullscreen_width = defaults.display.fullscreen_width;
            d.fullscreen_height = defaults.display.fullscreen_height;
            s.display.vsync = defaults.display.vsync;
            s.display.fps_limit = defaults.display.fps_limit;
            d.vsync = s.display.vsync;
            d.fps_limit = s.display.fps_limit;
            services_.apply_vsync();
            host.change_display(d);
            break;
        }
        case Tab::Graphics:
            s.graphics = defaults.graphics;
            services_.apply_graphics();
            break;
        case Tab::Audio: s.audio = defaults.audio; break;
        case Tab::Controls:
            s.input = defaults.input;
            binding_notice_.clear();
            break;
        case Tab::Interface:
            s.display.ui_scale = defaults.display.ui_scale;
            s.ui = defaults.ui;
            services_.apply_font();
            break;
        case Tab::Language:
            s.language = defaults.language;
            services_.apply_language();
            break;
        case Tab::Game: s.gameplay = defaults.gameplay; break;
        case Tab::Count: break;
    }
    services_.settings_changed();
}

}  // namespace sc
