// The menus and dialogs of UiHost in RmlUi (phase 126): the main menu
// (under the logo, which stays the game's own drawing), map generation,
// the game menu, who may come into a game, loading, messages and the
// display change's countdown. Each is a panel of rows (thing_rows.h) given
// every frame it shows; the buttons do what the old ones did.
#include <algorithm>
#include <cmath>

#include "core/speed.h"
#include "game/build_info.h"
#include "game/ui_host.h"
#include "i18n/translator.h"
#include "ui/rml/rml_ui.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint64_t kDisplayConfirmNs = 15'000'000'000ull;  // A display change waits this long for "Keep".

// A button that only runs `fn`.
RowButton act(ThingRows& out, std::string label, std::string tip, std::function<void()> fn, bool enabled = true,
              bool on = false) {
    return out.button(std::move(label), std::move(tip),
                      [fn = std::move(fn)](GameSession*, const RowInput&, RowEffects&) { fn(); }, enabled, on);
}

}  // namespace

void UiHost::menu(const std::string& id, ThingRows rows, float width, float y) {
    menus_.give(id, std::move(rows), y >= 0.0f ? RmlPanels::Place::Center : RmlPanels::Place::Screen, width, y);
}

void UiHost::main_menu(ui::Context& ctx) {
    const float margin = ctx.s(16.0f);
    const float cx = ctx.width() * 0.5f;
    struct Entry {
        const char* id;
        const char* label;
        const char* tooltip;
        bool available;
    };
    const Entry entries[] = {
        {"single", "menu.main.singlePlayer", "menu.main.singlePlayer.tooltip", true},
        {"tutorial", "menu.main.tutorial", "menu.main.tutorial.tooltip",
         services_.content() != nullptr && !services_.content()->tutorials.empty()},
        {"host", "menu.main.hostGame", "menu.main.hostGame.tooltip", true},
        {"join", "menu.main.joinGame", "menu.main.joinGame.tooltip", true},
        {"load", "menu.main.loadGame", "menu.main.loadGame.tooltip", true},
        {"mods", "menu.main.mods", "menu.main.mods.tooltip", true},
        {"settings", "menu.main.settings", "menu.main.settings.tooltip", true},
        {"quit", "menu.main.quit", "menu.main.quit.tooltip", true},
    };
    // The logo (the game's own drawing, with its glow) takes at most a third
    // of the window, and the buttons go below it.
    const float logo_max_h = std::max(ctx.s(40.0f), ctx.height() * 0.33f);
    float logo_h = 0.0f;
    draw_logo(ctx, cx, 0.0f, ctx.width() - 2 * margin, logo_max_h, logo_h, false);
    const float buttons_h = ctx.s(static_cast<float>(std::size(entries)) * 52.0f + 40.0f);
    const float notices_h = ctx.s(static_cast<float>(notices_.size()) * 90.0f);
    const float y = std::round(std::max(margin, (ctx.height() - logo_h - ctx.s(28.0f) - buttons_h - notices_h) * 0.5f));
    draw_logo(ctx, cx, y, ctx.width() - 2 * margin, logo_max_h, logo_h, true);

    ThingRows out;
    // Notices, each with a close button.
    for (std::size_t i = 0; i < notices_.size(); ++i) {
        RowButton close = act(out, {}, tr("menu.main.dismissNotice.tooltip"), [this, i] {
            if (i < notices_.size()) {
                notices_.erase(notices_.begin() + static_cast<std::ptrdiff_t>(i));
            }
        });
        close.icon = "icon-x";
        out.stepper(notices_[i], std::move(close), RowButton{});
        out.rows.back().cls = "notice";
    }
    for (const Entry& e : entries) {
        const std::string_view id = e.id;
        const std::string label = tr(e.label);
        out.buttons({act(out, label, tr(e.tooltip), [this, id, label, available = e.available] {
            if (!available) {
                show_message(tr("dialog.comingSoon.title"), tr("dialog.comingSoon.body", label));
            } else if (id == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MainMenu;
                screen_ = Screen::Load;
            } else if (id == "mods") {
                mods_screen_.open();
                screen_ = Screen::Mods;
            } else if (id == "tutorial") {
                start_tutorial(0);
            } else if (id == "single" || id == "host") {
                new_game_.open(services_.content(), id == "host", services_.settings().new_game);
                host_new_game_ = id == "host";
                screen_ = Screen::NewGame;
            } else if (id == "join") {
                join_.open();
                screen_ = Screen::Join;
            } else if (id == "settings") {
                open_settings();
            } else if (id == "quit") {
                services_.request_quit();
            }
        })});
        out.rows.back().cls = "big";
    }
    menu("main", std::move(out), 380.0f, y + logo_h + ctx.s(28.0f));

    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float version_h = ctx.text().line_height(small);
    ctx.label({margin, ctx.height() - margin - version_h, ctx.width() - 2 * margin, version_h},
              tr("menu.main.version", std::string(full_version())), small, ctx.theme().text_dim, ui::Align::Right);
}

void UiHost::generating_screen(ui::Context& ctx, bool modal) {
    const MapGenStatus status = services_.map_generation_status();
    if (status.state == MapGenStatus::State::Done) {
        if (services_.enter_generated_map()) {
            screen_ = Screen::MapView;
            game_menu_open_ = false;
            last_speed_ = speed::kNormal;
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
        "generating.step.relief",    "generating.step.lakes",  "generating.step.rivers",
        "generating.step.soil",      "generating.step.biomes", "generating.step.forests",
        "generating.step.resources", "generating.step.starts", "generating.step.view"};
    const int step = std::clamp(status.step, 0, kMapGenSteps - 1);
    const float overall = status.overall();
    const auto cancel = [this] {
        services_.cancel_map_generation();
        if (services_.net() != nullptr) {
            services_.leave_network();
            screen_ = Screen::MainMenu;
        } else {
            screen_ = Screen::NewGame;
        }
    };
    ThingRows out;
    out.line(tr("generating.title"), WinRow::Kind::Title);
    out.line(tr(kStepKeys[step]) + "  ·  " + tr("generating.percent", static_cast<int>(std::lround(overall * 100.0f))));
    out.line({}, WinRow::Kind::Meter).fraction = overall;
    out.buttons({act(out, tr("generating.cancel"), tr("generating.cancel.tooltip"), cancel)});
    menu("generating", std::move(out), 520.0f);
    if (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        cancel();
    }
}

void UiHost::game_menu(ui::Context& ctx) {
    struct Entry {
        const char* id;
        const char* label;
        const char* tooltip;
    };
    static constexpr Entry kEntries[] = {
        {"resume", "gameMenu.resume", "gameMenu.resume.tooltip"},
        {"save", "gameMenu.save", "gameMenu.save.tooltip"},
        {"load", "menu.main.loadGame", "menu.main.loadGame.tooltip"},
        {"open", "gameMenu.open", "gameMenu.open.tooltip"},
        {"access", "gameMenu.access", "gameMenu.access.tooltip"},
        {"watch", "gameMenu.watch", "gameMenu.watch.tooltip"},
        {"play", "gameMenu.play", "gameMenu.play.tooltip"},
        {"settings", "menu.main.settings", "menu.main.settings.tooltip"},
        {"leave", "gameMenu.leave", "gameMenu.leave.tooltip"},
        {"quit", "gameMenu.quit", "menu.main.quit.tooltip"},
    };
    if (access_dialog_) {
        access_dialog(ctx);
        return;
    }
    const bool playing = services_.session() != nullptr;
    const bool networked = playing && services_.session()->networked();
    ThingRows out;
    out.line(tr("gameMenu.title"), WinRow::Kind::Title);
    for (const Entry& e : kEntries) {
        const std::string_view id = e.id;
        // Loading a saved game is for single player only. Opening the game
        // to others too (phase 76), and not the tutorial's; once open, its
        // host changes who may come in.
        // Phase 79: a player goes to watch, where the game lets people
        // watch, and comes back to its town.
        const GameSession* session = services_.session();
        const bool seated = networked && session->seat() != GameSession::kNoSeat;
        const bool shown = id == "watch"    ? seated && !session->spectating() && (session->game().access() & sim::access::kWatch) != 0
                           : id == "play"   ? seated && session->spectating()
                           : id == "open"   ? playing && !networked && !tutorial_
                           : id == "access" ? services_.hosting()
                                            : (id != "save" && id != "load") || (id == "save" && playing) ||
                                                  (id == "load" && playing && !networked);
        if (!shown) {
            continue;
        }
        out.buttons({act(out, tr(e.label), tr(e.tooltip), [this, id] {
            if (id == "resume") {
                game_menu_open_ = false;
            } else if (id == "save") {
                services_.save_game();
            } else if (id == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MapView;
                screen_ = Screen::Load;
            } else if (id == "watch") {
                services_.watch_game();
                game_menu_open_ = false;
            } else if (id == "play") {
                services_.play_game(0);
                game_menu_open_ = false;
            } else if (id == "open" || id == "access") {
                if (services_.session() == nullptr) {
                    return;
                }
                // What the game allows now; a game never opened offers both.
                const std::uint8_t now = services_.session()->game().access();
                access_dialog_ = true;
                access_open_ = id == "open" || (now & sim::access::kOpen) != 0;
                access_join_ = id == "open" || (now & sim::access::kJoin) != 0;
                access_found_ = id == "open" || (now & sim::access::kFound) != 0;
                access_watch_ = id == "open" || (now & sim::access::kWatch) != 0;
            } else if (id == "settings") {
                settings_return_ = Screen::MapView;
                screen_ = Screen::Settings;
            } else if (id == "leave") {
                game_menu_open_ = false;
                leave_pending_ = true;  // With the next frame, out of RmlUi's event.
            } else {
                services_.request_quit();
            }
        })});
        out.rows.back().cls = "big";
    }
    menu("game_menu", std::move(out), 420.0f);
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        game_menu_open_ = false;
    }
}

// Phase 76. Who may come into the game: opening a single-player game to
// others, or changing it as the host.
void UiHost::access_dialog(ui::Context& ctx) {
    const bool hosting = services_.hosting();
    ThingRows out;
    out.line(tr(hosting ? "access.title.change" : "access.title.open"), WinRow::Kind::Title);
    struct Row {
        const char* label;
        bool* value;
        bool shown;
        bool enabled;
    };
    const Row rows[] = {
        {"access.open", &access_open_, hosting, true},
        {"access.join", &access_join_, true, access_open_ || !hosting},
        {"access.found", &access_found_, true, access_open_ || !hosting},
        {"access.watch", &access_watch_, true, true},
    };
    for (const Row& r : rows) {
        if (r.shown) {
            out.buttons({out.check(tr(r.label), tr(std::string(r.label) + ".tooltip"), r.value, r.enabled)});
            out.rows.back().cls = "checks";
        }
    }
    out.line(tr(hosting ? "access.note.change" : "access.note.open"), WinRow::Kind::Dim);
    // Opening the game (not hosting yet): open to play if it lets people
    // join or found; it may also be only to watch. Open to nobody's use is
    // no use: one thing at least.
    const bool open = hosting ? access_open_ : access_join_ || access_found_;
    const bool valid = hosting ? !access_open_ || access_join_ || access_found_ : access_join_ || access_found_ || access_watch_;
    const auto access = static_cast<std::uint8_t>((open ? sim::access::kOpen : 0) | (access_join_ ? sim::access::kJoin : 0) |
                                                  (access_found_ ? sim::access::kFound : 0) |
                                                  (access_watch_ ? sim::access::kWatch : 0));
    RowButton ok = act(
        out, tr(hosting ? "access.apply" : "access.confirm"), {},
        [this, hosting, access] {
            if (hosting) {
                services_.set_access(access);
            } else if (!services_.open_game(access)) {
                show_message(tr("access.failed.title"), tr("lobby.hostFailed.body"));
            }
            access_dialog_ = false;
            game_menu_open_ = false;
        },
        valid, true);
    out.buttons({std::move(ok), act(out, tr("access.back"), {}, [this] { access_dialog_ = false; })});
    menu("access", std::move(out), 520.0f);
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        access_dialog_ = false;
    }
}

void UiHost::load_screen(ui::Context& ctx, bool modal) {
    const auto back = [this] {
        screen_ = load_return_ == Screen::MapView && services_.current_map() != nullptr ? Screen::MapView : Screen::MainMenu;
    };
    ThingRows out;
    out.line(tr("load.title"), WinRow::Kind::Title);
    if (saves_.empty()) {
        out.line(tr("load.empty"), WinRow::Kind::Dim);
    }
    for (const save::Entry& e : saves_) {
        // The name and its details; phase 78: to play it or to host it for others.
        out.line(e.header.name, WinRow::Kind::Section).cls = e.readable ? "" : "off";
        const std::filesystem::path file = e.file;
        out.stepper(e.readable ? tr("load.detail", e.header.saved_at, static_cast<int>(e.header.population), e.header.game_version)
                               : tr("load.unreadable"),
                    act(
                        out, tr("load.host"), tr("load.host.tooltip"),
                        [this, file] {
                            if (services_.load_game_as_host(file)) {
                                lobby_screen_.open();
                                screen_ = Screen::Lobby;
                                game_menu_open_ = false;
                            }
                        },
                        e.readable && services_.scene_available()),
                    act(
                        out, tr("load.load"), tr("load.load.tooltip"),
                        [this, file] {
                            if (services_.load_game(file)) {
                                screen_ = Screen::MapView;
                                game_menu_open_ = false;
                            }
                        },
                        e.readable));
        out.rows.back().cls = "dimk";
    }
    out.buttons({act(out, tr("load.back"), tr("load.back.tooltip"), back)});
    menu("load", std::move(out), 640.0f);
    if (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        back();
    }
}

void UiHost::message_dialog(ui::Context& ctx) {
    const Message& m = messages_.front();
    ThingRows out;
    out.line(m.title, WinRow::Kind::Title);
    out.line(m.body, WinRow::Kind::Paragraph);
    out.buttons({act(
        out, tr("dialog.ok"), {},
        [this] {
            if (!messages_.empty()) {
                messages_.erase(messages_.begin());
            }
        },
        true, true)});
    menu("message", std::move(out), 560.0f);
    if (ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_ESCAPE) || ctx.input().key(SDL_SCANCODE_KP_ENTER)) {
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
    const auto revert = [this] {
        if (!pending_display_) {
            return;
        }
        const DisplaySettings previous = pending_display_->previous;
        pending_display_.reset();
        if (services_.apply_display(previous)) {
            services_.settings().display = previous;
            services_.settings_changed();
        }
    };
    ThingRows out;
    out.line(tr("dialog.keepDisplay.title"), WinRow::Kind::Title);
    out.line(i18n::tr_n("dialog.keepDisplay.body", seconds), WinRow::Kind::Paragraph);
    out.buttons({act(out, tr("dialog.keepDisplay.revert"), {}, revert),
                 act(out, tr("dialog.keepDisplay.keep"), {}, [this] { pending_display_.reset(); }, true, true)});
    menu("display", std::move(out), 560.0f);
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) || left_ns == 0) {
        revert();
    }
}

}  // namespace sc
