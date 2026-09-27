#include "game/ui_host.h"

#include <algorithm>
#include <cmath>

#include "core/text.h"
#include "i18n/translator.h"
#include "version.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint64_t kDisplayConfirmNs = 15'000'000'000ull;

// A centered dialog panel; returns the content rectangle.
ui::Rect dialog_frame(ui::Context& ctx, float content_height, std::string_view title, float& y) {
    const float pad = ctx.s(24.0f);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f));
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float h = std::min(ctx.height() - ctx.s(16.0f), content_height + title_h + 3 * pad);
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round((ctx.height() - h) * 0.5f), std::round(w),
                       std::round(h)};
    ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().overlay);
    ctx.panel(box);
    ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, title_h}, title,
              ctx.style(ctx.theme().heading, ui::FontRole::Bold), ctx.theme().accent, ui::Align::Left);
    y = box.y + pad + title_h + pad * 0.5f;
    return {box.x + pad, y, box.w - 2 * pad, box.bottom() - pad - y};
}

}  // namespace

UiHost::UiHost(Services& services)
    : services_(services),
      settings_screen_(services),
      mods_screen_(services),
      hud_(services),
      join_(services),
      lobby_screen_(services) {}

void UiHost::show_message(std::string title, std::string body) {
    messages_.push_back({std::move(title), std::move(body)});
}

void UiHost::add_notice(std::string text) {
    notices_.push_back(std::move(text));
}

void UiHost::toast(std::string text) {
    toast_ = std::move(text);
    toast_since_ns_ = 0;
}

void UiHost::draw_toast(ui::Context& ctx) {
    constexpr std::uint64_t kToastNs = 3'000'000'000ull;
    if (toast_.empty()) {
        return;
    }
    if (toast_since_ns_ == 0) {
        toast_since_ns_ = ctx.now_ns();
    }
    if (ctx.now_ns() - toast_since_ns_ > kToastNs) {
        toast_.clear();
        return;
    }
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.width() - ctx.s(32.0f), ctx.text().measure(st, toast_) + ctx.s(40.0f));
    const float h = ctx.text().line_height(st) + ctx.s(16.0f);
    const ui::Rect r{std::round((ctx.width() - w) * 0.5f), std::round(ctx.s(60.0f)), std::round(w), std::round(h)};
    ctx.draw().rect(r, ctx.theme().tooltip.with_alpha(0.9f));
    ctx.draw().rect_outline(r, ctx.theme().accent, std::max(1.0f, std::round(ctx.s(1.0f))));
    ctx.label(r, toast_, st, ctx.theme().text, ui::Align::Center);
}

bool UiHost::wants_keyboard() const {
    return screen_ == Screen::Settings && settings_screen_.capturing_key();
}

UiHost::SceneMode UiHost::scene_mode() const {
    if (!services_.scene_available()) {
        return SceneMode::None;
    }
    // Settings and the load list opened from the game keep the map behind them.
    const bool over_map = screen_ == Screen::MapView ||
                          (screen_ == Screen::Settings && settings_return_ == Screen::MapView) ||
                          (screen_ == Screen::Load && load_return_ == Screen::MapView);
    if (over_map && services_.current_map() != nullptr) {
        return SceneMode::Map;
    }
    return screen_ == Screen::TestScene ? SceneMode::TestScene : SceneMode::MenuBackground;
}

bool UiHost::scene_paused() const {
    if (scene_mode() != SceneMode::Map) {
        return false;
    }
    const bool menu = game_menu_open_ || screen_ == Screen::Settings || screen_ == Screen::Load;
    return menu || (services_.session() != nullptr && services_.game_speed() == 0);
}

bool UiHost::game_paused() const {
    const GameSession* s = services_.session();
    if (s == nullptr) {
        return true;
    }
    // A network game only stops when the players pause it.
    if (s->networked()) {
        return services_.game_speed() == 0;
    }
    return screen_ != Screen::MapView || game_menu_open_ || services_.game_speed() == 0;
}

void UiHost::follow_network() {
    net::NetSession* net = services_.net();
    if (net == nullptr) {
        if (screen_ == Screen::Lobby) {
            screen_ = Screen::MainMenu;
        }
        return;
    }
    // The host started: everybody builds the map; a game already running
    // is shown as soon as its state arrives.
    if (screen_ == Screen::Lobby && net->state() == net::NetSession::State::Loading) {
        screen_ = Screen::Generating;
    } else if ((screen_ == Screen::Lobby || screen_ == Screen::Generating) && services_.session() != nullptr &&
               net->state() == net::NetSession::State::Playing) {
        screen_ = Screen::MapView;
        game_menu_open_ = false;
    }
}

bool UiHost::modal_open() const {
    return !messages_.empty() || pending_display_.has_value();
}

void UiHost::change_display(const DisplaySettings& wanted) {
    DisplaySettings& current = services_.settings().display;
    const DisplaySettings previous = pending_display_ ? pending_display_->previous : current;
    if (!services_.apply_display(wanted)) {
        show_message(tr("dialog.displayFailed.title"), tr("dialog.displayFailed.body"));
        return;
    }
    current = wanted;
    services_.settings_changed();
    // Nothing risky changed if the result equals where we started.
    if (wanted.mode == previous.mode && wanted.monitor == previous.monitor &&
        wanted.fullscreen_width == previous.fullscreen_width &&
        wanted.fullscreen_height == previous.fullscreen_height) {
        pending_display_.reset();
        return;
    }
    // The countdown starts on the first frame drawn in the new mode.
    pending_display_ = PendingDisplay{previous, 0, false};
}

void UiHost::frame(ui::Context& ctx) {
    const bool modal = modal_open();
    // Behind the menus, the 3D scene shows through a dark veil.
    const SceneMode mode = scene_mode();
    if (mode == SceneMode::None) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background);
    } else if (mode == SceneMode::MenuBackground) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background.with_alpha(0.55f));
    } else if (scene_paused()) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background.with_alpha(0.45f));
    }

    follow_network();
    if (screen_ == Screen::TestScene) {
        ctx.set_input_blocked(modal);
        test_scene_hud(ctx);
    } else if (screen_ == Screen::NewGame) {
        ctx.set_input_blocked(modal);
        const NewGameScreen::Result r = new_game_.frame(ctx, modal);
        // The form is remembered however it is left (phase 23).
        if (r != NewGameScreen::Result::None && services_.settings().new_game != new_game_.remembered()) {
            services_.settings().new_game = new_game_.remembered();
            services_.settings_changed();
        }
        if (r == NewGameScreen::Result::Back) {
            screen_ = Screen::MainMenu;
            host_new_game_ = false;
        } else if (r == NewGameScreen::Result::Generate && host_new_game_) {
            host_new_game_ = false;
            if (services_.host_game(new_game_.settings(), new_game_.rules())) {
                lobby_screen_.open();
                screen_ = Screen::Lobby;
            } else {
                show_message(tr("lobby.hostFailed.title"), tr("lobby.hostFailed.body"));
            }
        } else if (r == NewGameScreen::Result::Generate) {
            services_.start_map_generation(new_game_.settings(), new_game_.rules());
            screen_ = Screen::Generating;
        }
    } else if (screen_ == Screen::Join) {
        ctx.set_input_blocked(modal);
        const JoinScreen::Result r = join_.frame(ctx, modal);
        if (r == JoinScreen::Result::Back) {
            screen_ = Screen::MainMenu;
        } else if (r == JoinScreen::Result::Joining) {
            lobby_screen_.open();
            screen_ = Screen::Lobby;
        }
    } else if (screen_ == Screen::Lobby) {
        ctx.set_input_blocked(modal);
        if (lobby_screen_.frame(ctx, modal) == LobbyScreen::Result::Leave) {
            services_.leave_network();
            screen_ = Screen::MainMenu;
        }
    } else if (screen_ == Screen::Generating) {
        ctx.set_input_blocked(modal);
        generating_screen(ctx, modal);
    } else if (screen_ == Screen::MapView) {
        ctx.set_input_blocked(modal);
        map_hud(ctx);
        if (screen_ != Screen::MapView) {
            tutorial_.reset();
        }
    } else if (screen_ == Screen::Load) {
        ctx.set_input_blocked(modal);
        load_screen(ctx, modal);
    } else if (screen_ == Screen::Mods) {
        if (!mods_screen_.frame(ctx, modal)) {
            screen_ = Screen::MainMenu;
        }
    } else if (screen_ == Screen::Settings) {
        if (!settings_screen_.frame(ctx, *this, modal)) {
            screen_ = settings_return_ == Screen::MapView && services_.current_map() != nullptr ? Screen::MapView
                                                                                                : Screen::MainMenu;
        }
    } else {
        ctx.set_input_blocked(modal);
        main_menu(ctx);
    }

    ctx.set_input_blocked(false);
    draw_toast(ctx);
    if (pending_display_) {
        display_confirm_dialog(ctx);
    } else if (!messages_.empty()) {
        message_dialog(ctx);
    }
}

void UiHost::draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                       bool draw) {
    const std::string top = tr("app.logo.top");
    const std::string bottom = tr("app.logo.bottom");
    // The first letter of the bottom line is drawn larger.
    std::size_t first_len = 0;
    if (!bottom.empty()) {
        (void)text::next_codepoint(bottom, first_len);
    }
    const std::string_view first = std::string_view(bottom).substr(0, first_len);
    const std::string_view rest = std::string_view(bottom).substr(first_len);

    float factor = 1.0f;
    ui::TextStyle top_style;
    ui::TextStyle big_style;
    ui::TextStyle rest_style;
    float top_w = 0.0f;
    float bottom_w = 0.0f;
    float top_h = 0.0f;
    float bottom_h = 0.0f;
    // Shrink until the logo fits both the width and its share of the height.
    for (int attempt = 0; attempt < 12; ++attempt) {
        top_style = ctx.style(static_cast<int>(42.0f * factor), ui::FontRole::Logo);
        big_style = ctx.style(static_cast<int>(118.0f * factor), ui::FontRole::Logo);
        rest_style = ctx.style(static_cast<int>(88.0f * factor), ui::FontRole::Logo);
        top_w = ctx.text().measure(top_style, top);
        bottom_w = ctx.text().measure(big_style, first) + ctx.text().measure(rest_style, rest);
        top_h = ctx.text().line_height(top_style);
        bottom_h = ctx.text().line_height(big_style);
        if (std::max(top_w, bottom_w) <= max_width && top_h + bottom_h * 0.9f <= max_height) {
            break;
        }
        factor *= 0.85f;
    }
    const float big_ascent = ctx.text().ascent(big_style);
    height_out = top_h + bottom_h * 0.9f;
    if (!draw) {
        return;
    }
    const ui::Color gold = ctx.theme().accent;
    ctx.text().draw(ctx.draw(), top_style, std::round(center_x - top_w * 0.5f), y, top, ctx.theme().text);
    const float baseline = std::round(y + top_h + big_ascent * 0.95f);
    float x = std::round(center_x - bottom_w * 0.5f);
    x += ctx.text().draw(ctx.draw(), big_style, x, baseline - big_ascent, first, gold);
    ctx.text().draw(ctx.draw(), rest_style, x, baseline - ctx.text().ascent(rest_style), rest, gold);
}

void UiHost::main_menu(ui::Context& ctx) {
    const float margin = ctx.s(16.0f);
    const float col_w = std::min(ctx.s(380.0f), ctx.width() - 2 * margin);
    const float cx = ctx.width() * 0.5f;
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);

    struct Entry {
        const char* id;
        std::string label;
        std::string tooltip;
        bool available;
    };
    const Entry entries[] = {
        {"single", tr("menu.main.singlePlayer"), tr("menu.main.singlePlayer.tooltip"), true},
        {"tutorial", tr("menu.main.tutorial"), tr("menu.main.tutorial.tooltip"),
         services_.content() != nullptr && !services_.content()->tutorials.empty()},
        {"host", tr("menu.main.hostGame"), tr("menu.main.hostGame.tooltip"), true},
        {"join", tr("menu.main.joinGame"), tr("menu.main.joinGame.tooltip"), true},
        {"load", tr("menu.main.loadGame"), tr("menu.main.loadGame.tooltip"), true},
        {"mods", tr("menu.main.mods"), tr("menu.main.mods.tooltip"), true},
        {"testScene", tr("menu.main.testScene"), tr("menu.main.testScene.tooltip"), services_.scene_available()},
        {"settings", tr("menu.main.settings"), tr("menu.main.settings.tooltip"), true},
        {"quit", tr("menu.main.quit"), tr("menu.main.quit.tooltip"), true},
    };

    // Measure first so the whole column can be centered or scrolled.
    // The logo takes at most a third of the window height.
    const float logo_max_h = std::max(ctx.s(40.0f), ctx.height() * 0.33f);
    float logo_h = 0.0f;
    draw_logo(ctx, cx, 0.0f, ctx.width() - 2 * margin, logo_max_h, logo_h, false);
    const ui::TextStyle notice_style = ctx.style(ctx.theme().body);
    float notices_h = 0.0f;
    for (const std::string& n : notices_) {
        notices_h += ctx.paragraph_height(col_w - ctx.s(64.0f), n, notice_style) + ctx.s(20.0f) + gap;
    }
    const float buttons_h = static_cast<float>(std::size(entries)) * (button_h + gap);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float version_h = ctx.text().line_height(small);
    const float content_h = notices_h + logo_h + ctx.s(36.0f) + buttons_h + margin * 2;
    // The version sits in the corner if there is room, otherwise below the
    // buttons, so it never covers them.
    const bool version_in_corner = content_h + 2 * version_h <= ctx.height();

    const ui::Rect viewport{0, 0, ctx.width(), ctx.height()};
    const float top = ctx.begin_scroll(ctx.id("main_menu"), viewport);
    float y = top + std::max(margin, (ctx.height() - content_h) * 0.5f + margin);

    // Notices, each with a close button.
    for (std::size_t i = 0; i < notices_.size();) {
        const float text_h = ctx.paragraph_height(col_w - ctx.s(64.0f), notices_[i], notice_style);
        const ui::Rect box{std::round(cx - col_w * 0.5f), std::round(y), std::round(col_w), std::round(text_h + ctx.s(20.0f))};
        ctx.draw().rect(box, ctx.theme().danger.with_alpha(0.35f));
        ctx.draw().rect_outline(box, ctx.theme().danger, std::max(1.0f, std::round(ctx.s(1.0f))));
        ctx.paragraph({box.x + ctx.s(10.0f), box.y + ctx.s(10.0f), box.w - ctx.s(64.0f), text_h}, notices_[i],
                      notice_style, ctx.theme().text);
        const float close = ctx.s(32.0f);
        ctx.push_id("notice");
        const bool closed = ctx.button(ctx.id(std::to_string(i)), {box.right() - close - ctx.s(8.0f), box.y + ctx.s(8.0f), close, close},
                                       "x", tr("menu.main.dismissNotice.tooltip"));
        ctx.pop_id();
        y += box.h + gap;
        if (closed) {
            notices_.erase(notices_.begin() + static_cast<std::ptrdiff_t>(i));
        } else {
            ++i;
        }
    }

    draw_logo(ctx, cx, y, ctx.width() - 2 * margin, logo_max_h, logo_h, true);
    y += logo_h + ctx.s(36.0f);

    for (const Entry& e : entries) {
        const ui::Rect r{std::round(cx - col_w * 0.5f), std::round(y), std::round(col_w), std::round(button_h)};
        if (ctx.button(ctx.id(e.id), r, e.label, e.tooltip)) {
            if (!e.available) {
                show_message(tr("dialog.comingSoon.title"), tr("dialog.comingSoon.body", e.label));
            } else if (std::string_view(e.id) == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MainMenu;
                screen_ = Screen::Load;
            } else if (std::string_view(e.id) == "mods") {
                mods_screen_.open();
                screen_ = Screen::Mods;
            } else if (std::string_view(e.id) == "tutorial") {
                start_tutorial(0);
            } else if (std::string_view(e.id) == "single") {
                new_game_.open(services_.content(), false, services_.settings().new_game);
                host_new_game_ = false;
                screen_ = Screen::NewGame;
            } else if (std::string_view(e.id) == "host") {
                new_game_.open(services_.content(), true, services_.settings().new_game);
                host_new_game_ = true;
                screen_ = Screen::NewGame;
            } else if (std::string_view(e.id) == "join") {
                join_.open();
                screen_ = Screen::Join;
            } else if (std::string_view(e.id) == "testScene") {
                screen_ = Screen::TestScene;
            } else if (std::string_view(e.id) == "settings") {
                open_settings();
            } else if (std::string_view(e.id) == "quit") {
                services_.request_quit();
            }
        }
        y += button_h + gap;
    }
    const std::string version = tr("menu.main.version", std::string(SC_VERSION_STRING));
    if (!version_in_corner) {
        ctx.label({margin, y, ctx.width() - 2 * margin, version_h}, version, small, ctx.theme().text_dim,
                  ui::Align::Center);
    }
    ctx.end_scroll(content_h + (version_in_corner ? 0.0f : version_h + margin));

    if (version_in_corner) {
        ctx.label({margin, ctx.height() - margin - version_h, ctx.width() - 2 * margin, version_h}, version, small,
                  ctx.theme().text_dim, ui::Align::Right);
    }
}

// The camera line names the current mode and the key that changes it.
std::string UiHost::camera_line() const {
    const char* mode_key = "camera.mode.aerial";
    if (services_.camera_mode() == CameraMode::ThirdPerson) {
        mode_key = "camera.mode.thirdPerson";
    } else if (services_.camera_mode() == CameraMode::FirstPerson) {
        mode_key = "camera.mode.firstPerson";
    }
    const std::string key = key_display_name(services_.settings().input.bindings.key(Action::CameraCycleMode, 0));
    return tr("testScene.camera", tr(mode_key), key);
}

void UiHost::generating_screen(ui::Context& ctx, bool modal) {
    const MapGenStatus status = services_.map_generation_status();
    if (status.state == MapGenStatus::State::Done) {
        if (services_.enter_generated_map()) {
            screen_ = Screen::MapView;
            game_menu_open_ = false;
            last_speed_ = 1;
        } else {
            show_message(tr("generating.showFailed.title"), tr("generating.showFailed.body"));
            screen_ = Screen::NewGame;
        }
        return;
    }
    if (status.state != MapGenStatus::State::Running) {
        if (services_.net() != nullptr) {
            return;  // The network game shows once its state is ready.
        }
        screen_ = Screen::NewGame;
        return;
    }

    static constexpr const char* kStepKeys[kMapGenSteps] = {
        "generating.step.relief",  "generating.step.lakes",     "generating.step.rivers",
        "generating.step.soil",    "generating.step.biomes",    "generating.step.forests",
        "generating.step.resources", "generating.step.starts",  "generating.step.view"};
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float bar_h = ctx.s(18.0f);
    const float button_h = ctx.s(44.0f);
    const float line_h = ctx.text().line_height(body);
    float y = 0.0f;
    const ui::Rect content =
        dialog_frame(ctx, line_h + ctx.s(12.0f) + bar_h + ctx.s(24.0f) + button_h, tr("generating.title"), y);
    const int step = std::clamp(status.step, 0, kMapGenSteps - 1);
    const float overall = status.overall();
    const std::string percent = tr("generating.percent", static_cast<int>(std::lround(overall * 100.0f)));
    ctx.label({content.x, y, content.w, line_h}, tr(kStepKeys[step]), body, ctx.theme().text);
    ctx.label({content.x, y, content.w, line_h}, percent, body, ctx.theme().text_dim, ui::Align::Right);
    y += line_h + ctx.s(12.0f);
    const ui::Rect bar{content.x, std::round(y), content.w, std::round(bar_h)};
    ctx.draw().rect(bar, ctx.theme().button_active);
    ctx.draw().rect({bar.x, bar.y, std::round(bar.w * overall), bar.h}, ctx.theme().accent);
    ctx.draw().rect_outline(bar, ctx.theme().panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
    const float bw = std::min(ctx.s(180.0f), content.w);
    const ui::Rect cancel{content.right() - bw, content.bottom() - button_h, bw, button_h};
    if (ctx.button(ctx.id("generating_cancel"), cancel, tr("generating.cancel"), tr("generating.cancel.tooltip")) ||
        (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        services_.cancel_map_generation();
        if (services_.net() != nullptr) {
            services_.leave_network();
            screen_ = Screen::MainMenu;
        } else {
            screen_ = Screen::NewGame;
        }
    }
}

void UiHost::game_keys(ui::Context& ctx) {
    const KeyBindings& b = services_.settings().input.bindings;
    for (const SDL_Scancode k : ctx.input().keys) {
        if (b.matches(Action::GamePause, k)) {
            if (services_.game_speed() == 0) {
                services_.set_game_speed(last_speed_);
            } else {
                last_speed_ = services_.game_speed();
                services_.set_game_speed(0);
            }
        } else if (b.matches(Action::GameSpeed1, k)) {
            services_.set_game_speed(1);
        } else if (b.matches(Action::GameSpeed2, k)) {
            services_.set_game_speed(2);
        } else if (b.matches(Action::GameSpeed3, k)) {
            services_.set_game_speed(3);
        } else if (b.matches(Action::GameQuickSave, k)) {
            services_.save_game();
        } else if (b.matches(Action::GameQuickLoad, k)) {
            const std::vector<save::Entry> saves = services_.list_saves();
            const auto it = std::find_if(saves.begin(), saves.end(), [](const save::Entry& e) { return e.readable; });
            if (it != saves.end()) {
                (void)services_.load_game(it->file);
            } else {
                show_message(tr("load.title"), tr("load.empty"));
            }
        }
    }
    if (services_.game_speed() > 0) {
        last_speed_ = services_.game_speed();
    }
}

void UiHost::pause_panel(ui::Context& ctx) {
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, 2 * button_h + gap, tr("pause.title"), y);
    if (ctx.button(ctx.id("pause_resume"), {content.x, std::round(y), content.w, std::round(button_h)},
                   tr("pause.resume"), tr("pause.resume.tooltip"), true, true)) {
        services_.set_game_speed(last_speed_);
    }
    y += button_h + gap;
    if (ctx.button(ctx.id("pause_menu"), {content.x, std::round(y), content.w, std::round(button_h)},
                   tr("gameMenu.title"), tr("pause.menu.tooltip"))) {
        game_menu_open_ = true;
    }
}

void UiHost::map_hud(ui::Context& ctx) {
    const sim::MapData* map = services_.current_map();
    if (map == nullptr) {
        screen_ = Screen::MainMenu;
        return;
    }
    if (services_.session() != nullptr) {
        const bool paused = services_.game_speed() == 0;
        if (!game_menu_open_ && !modal_open()) {
            game_keys(ctx);
        }
        ctx.set_input_blocked(modal_open() || game_menu_open_ || paused);
        if (tutorial_ && services_.content() != nullptr && tutorial_->def < services_.content()->tutorials.size()) {
            const sim::TutorialDef& t = services_.content()->tutorials[tutorial_->def];
            hud_.set_highlight(tutorial_->step < t.steps.size() ? t.steps[tutorial_->step].highlight : std::string());
        } else {
            hud_.set_highlight({});
        }
        const bool wants_menu = hud_.frame(ctx, modal_open() || game_menu_open_ || paused);
        if (tutorial_ && !game_menu_open_) {
            tutorial_panel(ctx);
        }
        ctx.set_input_blocked(modal_open());
        if (!services_.session()->game().game_over()) {
            end_seen_ = false;
        } else if (!end_seen_ && !game_menu_open_) {
            end_panel(ctx);
            return;
        }
        if (game_menu_open_) {
            game_menu(ctx);
        } else if (paused) {
            pause_panel(ctx);
            if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
                game_menu_open_ = true;
            }
        } else if (wants_menu && !modal_open()) {
            game_menu_open_ = true;
        }
        return;
    }
    const float pad = ctx.s(12.0f);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(600.0f), ctx.width() - 2 * pad);
    static constexpr const char* kSizeKeys[] = {"newGame.size.small", "newGame.size.medium", "newGame.size.large",
                                                "newGame.size.huge"};
    const auto size_index = static_cast<std::size_t>(map->settings.size);
    const std::string size = tr(kSizeKeys[std::min<std::size_t>(size_index, 3)], map->size);
    const std::string text = tr("map.info", std::to_string(map->settings.seed), size) + "\n" + tr("map.hint") + "\n" +
                             camera_line();
    const float h = ctx.paragraph_height(w - 2 * pad, text, st);
    const ui::Rect box{pad, pad, w, h + 2 * pad};
    ctx.draw().rect(box, ctx.theme().tooltip.with_alpha(0.8f));
    ctx.paragraph(box.inset(pad), text, st, ctx.theme().text);
    if (game_menu_open_) {
        game_menu(ctx);
    } else if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        game_menu_open_ = true;
    }
}

// Esc during a game: continue, settings, or leave. In phase 8 it will also
// pause a single-player game (decision D-616).
void UiHost::start_tutorial(std::size_t index) {
    const sim::Content* content = services_.content();
    if (content == nullptr || index >= content->tutorials.size()) {
        return;
    }
    const sim::TutorialDef& t = content->tutorials[index];
    sim::MapSettings map;
    map.seed = static_cast<std::uint64_t>(t.seed);
    map.size = static_cast<sim::MapSize>(t.size);
    map.players = 1;
    // A gentle start: no raiders, little danger.
    sim::GameRules rules;
    rules.raiders = sim::Threat::None;
    rules.wildlife = sim::Threat::Low;
    rules.diseases = sim::Threat::Low;
    rules.fires = sim::Threat::Low;
    tutorial_ = TutorialRun{};
    tutorial_->def = index;
    tutorial_lua_.reset();
    for (const sim::TutorialStep& step : t.steps) {
        if (step.goal == sim::TutorialGoal::Lua && !tutorial_lua_ && services_.mod_scripts() != nullptr) {
            tutorial_lua_ = std::make_unique<script::TutorialScript>();
            std::string error;
            if (!tutorial_lua_->open(*services_.mod_scripts(), t.mod, error)) {
                tutorial_->error = error;
                tutorial_lua_.reset();
            }
        }
    }
    services_.start_map_generation(map, rules);
    screen_ = Screen::Generating;
}

bool UiHost::tutorial_step_done(const sim::TutorialStep& step, std::uint64_t now_ns) {
    GameSession* s = services_.session();
    if (s == nullptr) {
        return false;
    }
    const sim::Game& game = s->game();
    const sim::Content& content = game.content();
    const std::uint8_t town = s->town();
    const auto count = [&](bool complete_only) {
        const sim::DefIndex d = content.find_building(step.target);
        std::int32_t n = 0;
        for (const sim::Building& b : game.buildings().data()) {
            n += b.owner == town && b.def == d && (!complete_only || b.state == sim::BuildingState::Complete) ? 1 : 0;
        }
        return n;
    };
    switch (step.goal) {
        case sim::TutorialGoal::None: return false;
        case sim::TutorialGoal::Camera: {
            const std::array<float, 3> now = services_.camera_view();
            const std::array<float, 3>& was = tutorial_->camera;
            return std::abs(now[0] - was[0]) + std::abs(now[1] - was[1]) > 15.0f || std::abs(now[2] - was[2]) > 10.0f;
        }
        case sim::TutorialGoal::Place: return count(false) >= step.amount;
        case sim::TutorialGoal::Build: return count(true) >= step.amount;
        case sim::TutorialGoal::Workers:
            for (const sim::Building& b : game.buildings().data()) {
                if (b.owner == town && !b.workers.empty()) {
                    return true;
                }
            }
            return false;
        case sim::TutorialGoal::Speed: return services_.game_speed() != tutorial_->speed;
        case sim::TutorialGoal::Stock: {
            const sim::DefIndex r = content.find_resource(step.target);
            return r != sim::kNoDef && game.stored(town)[r] >= step.amount;
        }
        case sim::TutorialGoal::Population: return game.population(town) >= step.amount;
        case sim::TutorialGoal::Lua: {
            if (!tutorial_lua_ || now_ns < tutorial_->next_lua_ns) {
                return false;
            }
            tutorial_->next_lua_ns = now_ns + 500'000'000ull;  // Twice a second.
            script::TutorialState st;
            st.population = game.population(town);
            const sim::Calendar cal = game.calendar();
            st.year = static_cast<std::int32_t>(cal.year);
            st.month = static_cast<std::int32_t>(cal.month);
            st.day = static_cast<std::int32_t>(cal.day);
            const std::vector<std::int32_t> stored = game.stored(town);
            for (std::size_t r = 0; r < stored.size(); ++r) {
                st.stored[content.resources[r].id] = stored[r];
            }
            for (const sim::Building& b : game.buildings().data()) {
                if (b.owner == town && b.state == sim::BuildingState::Complete) {
                    ++st.built[content.buildings[b.def].id];
                }
            }
            bool done = false;
            std::string error;
            if (!tutorial_lua_->check(step.target, st, done, error)) {
                tutorial_->error = error;
                return false;
            }
            return done;
        }
        case sim::TutorialGoal::Count: break;
    }
    return false;
}

void UiHost::tutorial_panel(ui::Context& ctx) {
    const sim::Content* content = services_.content();
    if (content == nullptr || tutorial_->def >= content->tutorials.size()) {
        tutorial_.reset();
        return;
    }
    const sim::TutorialDef& t = content->tutorials[tutorial_->def];
    if (tutorial_->step >= t.steps.size()) {
        tutorial_.reset();
        return;
    }
    const sim::TutorialStep& step = t.steps[tutorial_->step];
    if (!tutorial_->step_started) {
        tutorial_->step_started = true;
        tutorial_->camera = services_.camera_view();
        tutorial_->speed = services_.game_speed();
    }
    const bool last = tutorial_->step + 1 == t.steps.size();
    if (!last && tutorial_step_done(step, ctx.now_ns())) {
        ++tutorial_->step;
        tutorial_->step_started = false;
        return;
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float pad = ctx.s(14.0f);
    const float w = std::round(std::min(ctx.s(560.0f), ctx.width() - ctx.s(300.0f)));
    const float button_h = std::round(ctx.s(34.0f));
    const std::string text = tr(step.text_key);
    const float text_h = ctx.paragraph_height(w - 2 * pad, text, body);
    const float line = ctx.text().line_height(small);
    const float error_h = tutorial_->error.empty() ? 0.0f : line;
    const float h = pad + line + ctx.s(4.0f) + text_h + error_h + pad + button_h + pad;
    // Above the build bar, in the middle: the windows keep the top.
    const float bottom = hud_.build_bar_top() > 0.0f ? hud_.build_bar_top() : ctx.height() - ctx.s(110.0f);
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round(bottom - h - ctx.s(12.0f)), w, std::round(h)};
    ctx.panel(box);
    if (GameSession* s = services_.session()) {
        s->ui().hud_rects.push_back({box.x, box.y, box.w, box.h});
    }
    float y = box.y + pad;
    ctx.label({box.x + pad, y, box.w - 2 * pad, line},
              tr("tutorial.step", tr(t.name_key), static_cast<int>(tutorial_->step) + 1, static_cast<int>(t.steps.size())),
              small, ctx.theme().accent);
    y += line + ctx.s(4.0f);
    y += ctx.paragraph({box.x + pad, y, box.w - 2 * pad, text_h}, text, body, ctx.theme().text);
    if (!tutorial_->error.empty()) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("tutorial.scriptError"), small, ctx.theme().danger);
        y += line;
    }
    y += pad;
    const float bw = (box.w - 3 * pad) * 0.5f;
    if (last) {
        if (ctx.button(ctx.id("tutorial_finish"), {box.x + pad, y, box.w - 2 * pad, button_h}, tr("tutorial.finish"),
                       tr("tutorial.finish.tooltip"), true, true)) {
            services_.settings().gameplay.tutorial_seen = true;
            services_.settings_changed();
            tutorial_.reset();
        }
        return;
    }
    if (ctx.button(ctx.id("tutorial_skip"), {box.x + pad, y, bw, button_h}, tr("tutorial.skip"), tr("tutorial.skip.tooltip"))) {
        ++tutorial_->step;
        tutorial_->step_started = false;
    }
    if (ctx.button(ctx.id("tutorial_quit"), {box.x + 2 * pad + bw, y, bw, button_h}, tr("tutorial.quit"),
                   tr("tutorial.quit.tooltip"))) {
        tutorial_.reset();
    }
}

void UiHost::end_panel(ui::Context& ctx) {
    GameSession* s = services_.session();
    const sim::Game& game = s->game();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float line = ctx.text().line_height(body);
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);
    std::vector<std::uint8_t> towns;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_of(p) == p && game.player(p).active) {
            towns.push_back(p);
        }
    }
    const sim::Outcome mine = game.player(s->town()).outcome;
    const char* title = mine == sim::Outcome::Won ? "end.won" : mine == sim::Outcome::Lost ? "end.lost" : "end.over";
    const float content_h = line * static_cast<float>(towns.size() + 1) + gap + 2 * (button_h + gap);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, content_h, tr(title), y);
    ctx.label({content.x, y, content.w, line}, tr("end.header"), ctx.style(ctx.theme().small), ctx.theme().text_dim);
    y += line;
    static constexpr const char* kOutcomes[] = {"hud.outcome.playing", "hud.outcome.won", "hud.outcome.lost"};
    for (const std::uint8_t p : towns) {
        const sim::PlayerState& ps = game.player(p);
        std::string name = tr("hud.trade.town", static_cast<int>(p) + 1);
        if (net::NetSession* net = services_.net()) {
            for (const net::LobbyPlayer& lp : net->lobby().players) {
                name = lp.slot == p ? lp.name : name;
            }
        }
        ctx.label({content.x, y, content.w, line},
                  tr("end.row", name, tr(kOutcomes[static_cast<std::size_t>(ps.outcome) % 3]), game.score(p),
                     game.population(p), game.military_power(p)),
                  body, p == s->town() ? ctx.theme().accent : ctx.theme().text);
        y += line;
    }
    y += gap;
    if (ctx.button(ctx.id("end_watch"), {content.x, y, content.w, button_h}, tr("end.watch"), tr("end.watch.tooltip"))) {
        end_seen_ = true;
    }
    y += button_h + gap;
    if (ctx.button(ctx.id("end_leave"), {content.x, y, content.w, button_h}, tr("gameMenu.leave"),
                   tr("gameMenu.leave.tooltip"))) {
        end_seen_ = true;
        services_.leave_map();
        services_.leave_network();
        screen_ = Screen::MainMenu;
    }
}

void UiHost::game_menu(ui::Context& ctx) {
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);
    struct Entry {
        const char* id;
        const char* label;
        const char* tooltip;
    };
    static constexpr Entry kEntries[] = {
        {"resume", "gameMenu.resume", "gameMenu.resume.tooltip"},
        {"save", "gameMenu.save", "gameMenu.save.tooltip"},
        {"load", "menu.main.loadGame", "menu.main.loadGame.tooltip"},
        {"settings", "menu.main.settings", "menu.main.settings.tooltip"},
        {"leave", "gameMenu.leave", "gameMenu.leave.tooltip"},
        {"quit", "gameMenu.quit", "menu.main.quit.tooltip"},
    };
    const bool playing = services_.session() != nullptr;
    const bool networked = playing && services_.session()->networked();
    std::vector<const Entry*> entries;
    for (const Entry& e : kEntries) {
        const std::string_view id = e.id;
        // Loading a saved game is for single player only.
        if ((id != "save" && id != "load") || (id == "save" && playing) || (id == "load" && playing && !networked)) {
            entries.push_back(&e);
        }
    }
    const float content_h = static_cast<float>(entries.size()) * (button_h + gap) - gap;
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, content_h, tr("gameMenu.title"), y);
    for (const Entry* ep : entries) {
        const Entry& e = *ep;
        const ui::Rect r{content.x, std::round(y), content.w, std::round(button_h)};
        if (ctx.button(ctx.id(std::string("game_menu_") + e.id), r, tr(e.label), tr(e.tooltip))) {
            const std::string_view id = e.id;
            if (id == "resume") {
                game_menu_open_ = false;
            } else if (id == "save") {
                services_.save_game();
            } else if (id == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MapView;
                screen_ = Screen::Load;
            } else if (id == "settings") {
                settings_return_ = Screen::MapView;
                screen_ = Screen::Settings;
            } else if (id == "leave") {
                game_menu_open_ = false;
                services_.leave_map();
                services_.leave_network();
                screen_ = Screen::MainMenu;
            } else {
                services_.request_quit();
            }
            return;
        }
        y += button_h + gap;
    }
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        game_menu_open_ = false;
    }
}

void UiHost::load_screen(ui::Context& ctx, bool modal) {
    const float button_h = ctx.s(44.0f);
    const float row_h = ctx.s(64.0f);
    const float gap = ctx.s(8.0f);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float list_h = saves_.empty() ? ctx.text().line_height(body)
                                        : std::min(ctx.height() * 0.6f, static_cast<float>(saves_.size()) * (row_h + gap));
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, list_h + gap * 2 + button_h, tr("load.title"), y);
    bool back = false;
    if (saves_.empty()) {
        ctx.label({content.x, y, content.w, list_h}, tr("load.empty"), body, ctx.theme().text_dim);
    } else {
        const ui::Rect view{content.x, y, content.w, list_h};
        float ry = ctx.begin_scroll(ctx.id("load_list"), view);
        const float bw = std::min(ctx.s(140.0f), content.w * 0.3f);
        for (std::size_t i = 0; i < saves_.size(); ++i) {
            const save::Entry& e = saves_[i];
            const ui::Rect row{content.x, ry, content.w - ctx.s(12.0f), row_h};
            ctx.draw().rect(row, ctx.theme().button_active.with_alpha(0.6f));
            const float line = ctx.text().line_height(body);
            ctx.label({row.x + gap, row.y + gap, row.w - bw - 3 * gap, line}, e.header.name, body,
                      e.readable ? ctx.theme().text : ctx.theme().text_disabled);
            const std::string detail = e.readable ? tr("load.detail", e.header.saved_at, static_cast<int>(e.header.population),
                                                       e.header.game_version)
                                                  : tr("load.unreadable");
            ctx.label({row.x + gap, row.y + gap + line, row.w - bw - 3 * gap, ctx.text().line_height(small)}, detail, small,
                      ctx.theme().text_dim);
            ctx.push_id("load_row");
            if (ctx.button(ctx.id(std::to_string(i)), {row.right() - bw - gap, row.y + (row_h - button_h) * 0.5f, bw, button_h},
                           tr("load.load"), tr("load.load.tooltip"), e.readable)) {
                if (services_.load_game(e.file)) {
                    screen_ = Screen::MapView;
                    game_menu_open_ = false;
                    ctx.pop_id();
                    ctx.end_scroll(static_cast<float>(saves_.size()) * (row_h + gap));
                    return;
                }
            }
            ctx.pop_id();
            ry += row_h + gap;
        }
        ctx.end_scroll(static_cast<float>(saves_.size()) * (row_h + gap));
    }
    const float bw = std::min(ctx.s(180.0f), content.w);
    back = ctx.button(ctx.id("load_back"), {content.right() - bw, content.bottom() - button_h, bw, button_h},
                      tr("load.back"), tr("load.back.tooltip")) ||
           (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE));
    if (back) {
        screen_ = load_return_ == Screen::MapView && services_.current_map() != nullptr ? Screen::MapView
                                                                                         : Screen::MainMenu;
    }
}

void UiHost::test_scene_hud(ui::Context& ctx) {
    const float pad = ctx.s(12.0f);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(560.0f), ctx.width() - 2 * pad);
    const std::string text = tr("testScene.hint") + "\n" + camera_line() + "\n" +
                             tr(services_.camera_mode() == CameraMode::FirstPerson ? "testScene.follow.firstPerson"
                                                                                   : "testScene.follow");
    const float h = ctx.paragraph_height(w - 2 * pad, text, st);
    const ui::Rect box{pad, pad, w, h + 2 * pad};
    ctx.draw().rect(box, ctx.theme().tooltip.with_alpha(0.8f));
    ctx.paragraph(box.inset(pad), text, st, ctx.theme().text);
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        screen_ = Screen::MainMenu;
    }
}

void UiHost::message_dialog(ui::Context& ctx) {
    const Message& m = messages_.front();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f)) - 2 * ctx.s(24.0f);
    const float text_h = ctx.paragraph_height(w, m.body, body);
    const float button_h = ctx.s(44.0f);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, text_h + ctx.s(20.0f) + button_h, m.title, y);
    ctx.paragraph({content.x, y, content.w, text_h}, m.body, body, ctx.theme().text);
    const float bw = std::min(ctx.s(160.0f), content.w);
    const ui::Rect ok{content.right() - bw, content.bottom() - button_h, bw, button_h};
    const bool enter = ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_ESCAPE) ||
                       ctx.input().key(SDL_SCANCODE_KP_ENTER);
    if (ctx.button(ctx.id("message_ok"), ok, tr("dialog.ok"), {}, true, true) || enter) {
        messages_.erase(messages_.begin());
    }
}

void UiHost::display_confirm_dialog(ui::Context& ctx) {
    PendingDisplay& p = *pending_display_;
    if (!p.started) {
        p.started = true;
        p.deadline_ns = ctx.now_ns() + kDisplayConfirmNs;
    }
    const std::uint64_t left_ns = p.deadline_ns > ctx.now_ns() ? p.deadline_ns - ctx.now_ns() : 0;
    const auto seconds = static_cast<std::int64_t>((left_ns + 999'999'999ull) / 1'000'000'000ull);

    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const std::string text = i18n::tr_n("dialog.keepDisplay.body", seconds);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f)) - 2 * ctx.s(24.0f);
    const float text_h = ctx.paragraph_height(w, text, body);
    const float button_h = ctx.s(44.0f);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, text_h + ctx.s(20.0f) + button_h, tr("dialog.keepDisplay.title"), y);
    ctx.paragraph({content.x, y, content.w, text_h}, text, body, ctx.theme().text);

    const float gap = ctx.s(12.0f);
    const float bw = std::min(ctx.s(180.0f), (content.w - gap) * 0.5f);
    const ui::Rect keep{content.right() - bw, content.bottom() - button_h, bw, button_h};
    const ui::Rect revert{keep.x - gap - bw, keep.y, bw, button_h};
    const bool keep_clicked = ctx.button(ctx.id("display_keep"), keep, tr("dialog.keepDisplay.keep"), {}, true, true);
    const bool revert_clicked = ctx.button(ctx.id("display_revert"), revert, tr("dialog.keepDisplay.revert")) ||
                                ctx.input().key(SDL_SCANCODE_ESCAPE);
    if (keep_clicked) {
        pending_display_.reset();
    } else if (revert_clicked || left_ns == 0) {
        const DisplaySettings previous = p.previous;
        pending_display_.reset();
        if (services_.apply_display(previous)) {
            services_.settings().display = previous;
            services_.settings_changed();
        }
    }
}

}  // namespace sc
