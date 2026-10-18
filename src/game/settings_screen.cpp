#include "game/settings_screen.h"

#include <algorithm>
#include <cmath>
#include <format>
#include <functional>
#include <string>

#include "game/ui_host.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr int kFpsOptions[] = {0, 30, 60, 90, 120, 144, 165, 240};
// 0 is "automatic", the same as 100 % of the screen scale (decision D-207).
constexpr double kScaleOptions[] = {0.0, 0.75, 0.9, 1.1, 1.25, 1.5, 1.75, 2.0};
constexpr int kAutosaveOptions[] = {0, 5, 10, 15, 30, 60};

std::string percent(int v) {
    return tr("settings.value.percent", v);
}

// Four-level options ("off/low/medium/high" and similar) from text keys.
std::vector<std::string> level_options(const std::string& base) {
    std::vector<std::string> out;
    for (int i = 0; i < 4; ++i) {
        out.push_back(tr(base + "." + std::to_string(i)));
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

bool SettingsScreen::frame(ui::Context& ctx, UiHost& host, bool input_blocked) {
    if (capture_) {
        // A binding waits for its key: the first one pressed.
        if (!ctx.input().keys.empty()) {
            key_pressed(ctx.input().keys.front());
        }
        ThingRows wait;
        wait.line(tr("settings.controls.capture", tr("action." + std::string(action_info(capture_ ? capture_->action : Action{}).id))),
                  WinRow::Kind::Paragraph);
        if (capture_) {
            host.menu("capture", std::move(wait), 520.0f);
        }
    } else if (!input_blocked && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        leave_ = true;
    }
    host.menu("settings", rows(host), 900.0f);
    const bool stay = !leave_;
    leave_ = false;
    return stay;
}

ThingRows SettingsScreen::rows(UiHost& host) {
    ThingRows out;
    out.line(tr("settings.title"), WinRow::Kind::Title);
    static constexpr const char* kTabKeys[] = {"display", "graphics", "audio", "controls", "interface", "language", "game"};
    std::vector<RowButton> tabs;
    for (std::size_t i = 0; i < std::size(kTabKeys); ++i) {
        const auto t = static_cast<Tab>(i);
        tabs.push_back(out.button(tr(std::string("settings.tab.") + kTabKeys[i]), {}, row_run([this, t] { tab_ = t; }), true, tab_ == t));
    }
    out.buttons(std::move(tabs));
    out.rows.back().cls = "tabs";
    switch (tab_) {
        case Tab::Display: tab_display(out, host); break;
        case Tab::Graphics: tab_graphics(out); break;
        case Tab::Audio: tab_audio(out); break;
        case Tab::Controls: tab_controls(out); break;
        case Tab::Interface: tab_interface(out); break;
        case Tab::Language: tab_language(out); break;
        case Tab::Game: tab_game(out); break;
        case Tab::Count: break;
    }
    RowButton back = out.button(tr("settings.back"), {}, row_run([this] { leave_ = true; }), true, true);
    out.buttons({out.button(tr("settings.restoreDefaults"), tr("settings.restoreDefaults.tooltip"),
                            row_run([this, &host] { restore_tab_defaults(host); })),
                 std::move(back)});
    out.rows.back().cls = "big";
    return out;
}

void SettingsScreen::key_pressed(SDL_Scancode key) {
    if (!capture_) {
        return;
    }
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
        binding_notice_ =
            tr("settings.controls.moved", key_display_name(key), tr("action." + std::string(action_info(other).id)));
    }
    bindings.set_key(c.action, c.slot, key);
    services_.settings_changed();
}

void SettingsScreen::tab_display(ThingRows& out, UiHost& host) {
    const DisplaySettings& d = services_.settings().display;
    UiHost* h = &host;
    // Mode.
    {
        static constexpr WindowMode kModes[] = {WindowMode::Fullscreen, WindowMode::Borderless, WindowMode::Windowed};
        const int index = static_cast<int>(std::find(std::begin(kModes), std::end(kModes), d.mode) - std::begin(kModes));
        row_pick(out, tr("settings.display.mode"), tr("settings.display.mode.tooltip"),
             {tr("settings.display.mode.fullscreen"), tr("settings.display.mode.borderless"), tr("settings.display.mode.windowed")},
             index, true, [this, h](int i) {
                 DisplaySettings next = services_.settings().display;
                 next.mode = kModes[static_cast<std::size_t>(i)];
                 h->change_display(next);
             });
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
        row_pick(out, tr("settings.display.monitor"), tr("settings.display.monitor.tooltip"), options, index, true,
             [this, h, monitors](int i) {
                 DisplaySettings next = services_.settings().display;
                 next.monitor = i == 0 ? std::string{} : monitors[static_cast<std::size_t>(i - 1)];
                 h->change_display(next);
             });
    }
    // Resolution (exclusive fullscreen only).
    {
        const std::vector<Resolution> modes = services_.fullscreen_resolutions(d.monitor);
        std::vector<std::string> options = {tr("settings.display.resolution.desktop")};
        int index = 0;
        for (std::size_t i = 0; i < modes.size(); ++i) {
            options.push_back(
                tr("settings.display.resolution.value", std::to_string(modes[i].width), std::to_string(modes[i].height)));
            if (modes[i].width == d.fullscreen_width && modes[i].height == d.fullscreen_height) {
                index = static_cast<int>(i) + 1;
            }
        }
        const bool enabled = d.mode == WindowMode::Fullscreen;
        row_pick(out, tr("settings.display.resolution"),
             tr(enabled ? "settings.display.resolution.tooltip" : "settings.display.resolution.disabledTooltip"), options,
             index, enabled, [this, h, modes](int i) {
                 DisplaySettings next = services_.settings().display;
                 next.fullscreen_width = i == 0 ? 0 : modes[static_cast<std::size_t>(i - 1)].width;
                 next.fullscreen_height = i == 0 ? 0 : modes[static_cast<std::size_t>(i - 1)].height;
                 h->change_display(next);
             });
    }
    // VSync and frame limit apply at once; they cannot break the display.
    row_tick(out, tr("settings.display.vsync"), tr("settings.display.vsync.tooltip"), d.vsync, true, [this](bool v) {
        services_.settings().display.vsync = v;
        services_.apply_vsync();
        services_.settings_changed();
    });
    {
        std::vector<std::string> options;
        for (const int fps : kFpsOptions) {
            options.push_back(fps == 0 ? tr("settings.display.fpsLimit.none") : tr("settings.display.fpsLimit.value", fps));
        }
        const bool enabled = !d.vsync;
        row_pick(out, tr("settings.display.fpsLimit"),
             tr(enabled ? "settings.display.fpsLimit.tooltip" : "settings.display.fpsLimit.disabledTooltip"), options,
             closest_index(kFpsOptions, d.fps_limit), enabled, [this](int i) {
                 services_.settings().display.fps_limit = kFpsOptions[static_cast<std::size_t>(i)];
                 services_.settings_changed();
             });
    }
}

void SettingsScreen::tab_graphics(ThingRows& out) {
    GraphicsSettings& g = services_.settings().graphics;
    const auto changed = [this] {
        GraphicsSettings& gs = services_.settings().graphics;
        gs.preset = gs.matching_preset();
        services_.apply_graphics();
        services_.settings_changed();
    };
    row_pick(out, tr("settings.graphics.preset"), tr("settings.graphics.preset.tooltip"),
         {tr("settings.graphics.preset.low"), tr("settings.graphics.preset.medium"), tr("settings.graphics.preset.high"),
          tr("settings.graphics.preset.ultra"), tr("settings.graphics.preset.custom")},
         static_cast<int>(g.preset), true, [this, changed](int i) {
             const auto p = static_cast<QualityPreset>(i);
             if (p != QualityPreset::Custom) {
                 services_.settings().graphics.apply_preset(p);
             }
             changed();
         });
    struct Level {
        const char* key;
        int* value;
    };
    const Level levels[] = {{"shadows", &g.shadows},
                            {"drawDistance", &g.draw_distance},
                            {"vegetation", &g.vegetation},
                            {"groundDetail", &g.ground_detail},
                            {"antialiasing", &g.antialiasing}};
    for (const Level& l : levels) {
        const std::string base = std::string("settings.graphics.") + l.key;
        int* value = l.value;
        row_pick(out, tr(base), tr(base + ".tooltip"), level_options(base + ".level"), *l.value, true, [value, changed](int i) {
            *value = i;
            changed();
        });
    }
}

void SettingsScreen::tab_audio(ThingRows& out) {
    AudioSettings& a = services_.settings().audio;
    out.line(tr("settings.audio.pendingNote"), WinRow::Kind::Dim);
    struct Volume {
        const char* key;
        int* value;
    };
    const Volume volumes[] = {{"master", &a.master}, {"effects", &a.effects}, {"ambient", &a.ambient}, {"music", &a.music}, {"ui", &a.ui}};
    for (const Volume& v : volumes) {
        const std::string base = std::string("settings.audio.") + v.key;
        int* value = v.value;
        row_slide(out, tr(base) + ": " + percent(*v.value), tr(base + ".tooltip"), *v.value, 0, 100, 5, true, [this, value](int x) {
            if (*value != x) {
                *value = x;
                services_.settings_changed();
            }
        });
    }
}

void SettingsScreen::tab_controls(ThingRows& out) {
    InputSettings& in = services_.settings().input;
    out.line(tr("settings.controls.camera"), WinRow::Kind::Section);
    struct Speed {
        const char* key;
        double* value;
    };
    const Speed speeds[] = {{"panSpeed", &in.camera_pan_speed}, {"rotateSpeed", &in.camera_rotate_speed}, {"zoomSpeed", &in.camera_zoom_speed}};
    for (const Speed& sp : speeds) {
        const std::string base = std::string("settings.controls.") + sp.key;
        const int pct = static_cast<int>(std::lround(*sp.value * 100.0));
        double* value = sp.value;
        row_slide(out, tr(base) + ": " + percent(pct), tr(base + ".tooltip"), pct, 25, 400, 5, true, [this, value](int x) {
            const double v = static_cast<double>(x) / 100.0;
            if (*value != v) {
                *value = v;
                services_.settings_changed();
            }
        });
    }
    row_tick(out, tr("settings.controls.invertZoom"), tr("settings.controls.invertZoom.tooltip"), in.invert_zoom, true, [this](bool v) {
        services_.settings().input.invert_zoom = v;
        services_.settings_changed();
    });
    row_tick(out, tr("settings.controls.edgeScroll"), tr("settings.controls.edgeScroll.tooltip"), in.edge_scroll, true, [this](bool v) {
        services_.settings().input.edge_scroll = v;
        services_.settings_changed();
    });
    if (!binding_notice_.empty()) {
        out.line(binding_notice_, WinRow::Kind::Accent);
    }
    const ActionGroup groups[] = {ActionGroup::Camera, ActionGroup::Game, ActionGroup::Interface};
    const char* group_keys[] = {"settings.controls.group.camera", "settings.controls.group.game", "settings.controls.group.interface"};
    for (std::size_t gi = 0; gi < std::size(groups); ++gi) {
        out.line(tr(group_keys[gi]), WinRow::Kind::Section);
        for (const ActionInfo& info : action_table()) {
            if (info.group != groups[gi]) {
                continue;
            }
            const std::string name = tr("action." + std::string(info.id));
            const std::string tip = tr("settings.controls.binding.tooltip", name);
            std::vector<RowButton> keys;
            for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
                const SDL_Scancode key = in.bindings.key(info.action, slot);
                const bool active = capture_ && capture_->action == info.action && capture_->slot == slot;
                const Action action = info.action;
                keys.push_back(out.button(key == SDL_SCANCODE_UNKNOWN ? tr("settings.controls.unbound") : key_display_name(key), tip,
                                          row_run([this, action, slot] {
                                              capture_ = Capture{action, slot};
                                              binding_notice_.clear();
                                          }),
                                          true, active));
            }
            out.stepper(name, keys.size() > 0 ? keys[0] : RowButton{}, keys.size() > 1 ? keys[1] : RowButton{});
            out.rows.back().tip = tip;
            out.rows.back().cls = "wide keys";
        }
    }
}

void SettingsScreen::tab_interface(ThingRows& out) {
    Settings& s = services_.settings();
    {
        std::vector<std::string> options;
        for (const double scale : kScaleOptions) {
            options.push_back(scale == 0.0 ? tr("settings.interface.scale.auto") : percent(static_cast<int>(std::lround(scale * 100.0))));
        }
        row_pick(out, tr("settings.interface.scale"), tr("settings.interface.scale.tooltip"), options,
             s.display.ui_scale == 1.0 ? 0 : closest_index(kScaleOptions, s.display.ui_scale), true, [this](int i) {
                 services_.settings().display.ui_scale = kScaleOptions[static_cast<std::size_t>(i)];
                 services_.settings_changed();
             });
    }
    {
        const auto& families = services_.fonts().ui_families();
        std::vector<std::string> options;
        std::vector<std::string> ids;
        int index = 0;
        for (std::size_t i = 0; i < families.size(); ++i) {
            options.push_back(families[i].name);
            ids.push_back(families[i].id);
            if (families[i].id == s.ui.font) {
                index = static_cast<int>(i);
            }
        }
        if (!options.empty()) {
            row_pick(out, tr("settings.interface.font"), tr("settings.interface.font.tooltip"), options, index, true, [this, ids](int i) {
                services_.settings().ui.font = ids[static_cast<std::size_t>(i)];
                services_.apply_font();
                services_.settings_changed();
            });
        }
    }
    // The style of the interface (phase 119), with its colors as a preview,
    // and its glass; both apply at once.
    if (const std::vector<UiStyleChoice> styles = services_.ui_styles(); !styles.empty()) {
        std::vector<std::string> options;
        std::vector<std::string> ids;
        int index = 0;
        for (std::size_t i = 0; i < styles.size(); ++i) {
            options.push_back(styles[i].name);
            ids.push_back(styles[i].id);
            if (styles[i].id == s.ui.style) {
                index = static_cast<int>(i);
            }
        }
        row_pick(out, tr("settings.interface.style"), tr("settings.interface.style.tooltip"), options, index, true, [this, ids](int i) {
            services_.settings().ui.style = ids[static_cast<std::size_t>(i)];
            services_.settings_changed();
        });
        const std::vector<std::uint32_t>& colors = styles[static_cast<std::size_t>(index)].preview;
        if (!colors.empty()) {
            const auto css = [](std::uint32_t c) { return std::format("#{:06x}", c >> 8); };
            std::string swatches = "<div class=\"swatches\" style=\"background-color: " + css(colors[0]) + ";\">";
            for (std::size_t i = 1; i < colors.size(); ++i) {
                swatches += "<div class=\"swatch\" style=\"background-color: " + css(colors[i]) + ";\"></div>";
            }
            out.line(swatches + "</div>", WinRow::Kind::Raw);
        }
        row_pick(out, tr("settings.interface.glass"), tr("settings.interface.glass.tooltip"),
             {tr("settings.interface.glass.full"), tr("settings.interface.glass.simple")}, s.ui.glass == UiGlass::Simple ? 1 : 0,
             true, [this](int i) {
                 services_.settings().ui.glass = i == 1 ? UiGlass::Simple : UiGlass::Full;
                 services_.settings_changed();
             });
    }
    row_tick(out, tr("settings.interface.tooltips"), tr("settings.interface.tooltips.tooltip"), s.ui.show_tooltips, true, [this](bool v) {
        services_.settings().ui.show_tooltips = v;
        services_.settings_changed();
    });
    row_slide(out, tr("settings.interface.tooltipDelay") + ": " + tr("settings.value.ms", s.ui.tooltip_delay_ms),
          tr("settings.interface.tooltipDelay.tooltip"), s.ui.tooltip_delay_ms, 0, settings_limits::kMaxTooltipDelayMs, 100,
          s.ui.show_tooltips, [this](int v) {
              if (services_.settings().ui.tooltip_delay_ms != v) {
                  services_.settings().ui.tooltip_delay_ms = v;
                  services_.settings_changed();
              }
          });
}

void SettingsScreen::tab_language(ThingRows& out) {
    Settings& s = services_.settings();
    const bool is_auto = s.language == "auto";
    const auto choose = [this](std::string code) {
        return row_run([this, code] {
            services_.settings().language = code;
            services_.apply_language();
            services_.settings_changed();
        });
    };
    out.buttons({out.button(tr("settings.language.auto"), tr("settings.language.auto.tooltip"), choose("auto"), true, is_auto)});
    for (const i18n::LanguageInfo* lang : i18n::translator().available()) {
        out.buttons({out.button(lang->native_name, {}, choose(lang->code), true, !is_auto && s.language == lang->code)});
    }
    out.line(tr("settings.language.addHint"), WinRow::Kind::Dim);
}

void SettingsScreen::tab_game(ThingRows& out) {
    const GameplaySettings& g = services_.settings().gameplay;
    {
        std::vector<std::string> options;
        for (const int minutes : kAutosaveOptions) {
            options.push_back(minutes == 0 ? tr("settings.game.autosave.off") : i18n::tr_n("settings.game.autosave.minutes", minutes));
        }
        row_pick(out, tr("settings.game.autosave"), tr("settings.game.autosave.tooltip"), options,
             closest_index(kAutosaveOptions, g.autosave_minutes), true, [this](int i) {
                 services_.settings().gameplay.autosave_minutes = kAutosaveOptions[static_cast<std::size_t>(i)];
                 services_.settings_changed();
             });
    }
    row_slide(out, tr("settings.game.autosaveKeep") + ": " + i18n::tr_n("settings.game.autosaveKeep.value", g.autosave_keep),
          tr("settings.game.autosaveKeep.tooltip"), g.autosave_keep, 1, settings_limits::kMaxAutosaveKeep, 1, g.autosave_minutes > 0,
          [this](int v) {
              if (services_.settings().gameplay.autosave_keep != v) {
                  services_.settings().gameplay.autosave_keep = v;
                  services_.settings_changed();
              }
          });
    out.stepper(tr("settings.game.tutorial"),
                out.button(tr("settings.game.tutorial.button"), tr("settings.game.tutorial.tooltip"), row_run([this] {
                               services_.settings().gameplay.tutorial_seen = false;
                               services_.settings_changed();
                           }),
                           g.tutorial_seen),
                RowButton{});
    out.rows.back().cls = "wide";
    out.stepper(tr("settings.game.dataFolder"),
                out.button(tr("settings.game.dataFolder.button"), tr("settings.game.dataFolder.tooltip"),
                           row_run([this] { services_.open_data_folder(); })),
                RowButton{});
    out.rows.back().cls = "wide";
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
