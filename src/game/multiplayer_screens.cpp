#include "game/multiplayer_screens.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <format>

#include "game/new_game_screen.h"
#include "game/ui_host.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint32_t kPlayerColors[net::kColors] = {0xD9463B, 0x3B7BD9, 0x4DAF4A, 0xE8C33A, 0x984EA3, 0xF08A24,
                                                        0x3BC1C9, 0xE377C2, 0x8C564B, 0xBCBD22, 0xF4F4F4, 0x333333};

bool parse_port(std::string_view text, std::uint16_t& port) {
    int value = 0;
    const auto r = std::from_chars(text.data(), text.data() + text.size(), value);
    if (r.ec != std::errc{} || r.ptr != text.data() + text.size() || value < 1024 || value > 65535) {
        return false;
    }
    port = static_cast<std::uint16_t>(value);
    return true;
}

}  // namespace

ui::Color player_color(std::uint8_t index) {
    return ui::Color::rgb(kPlayerColors[index % net::kColors]);
}

// --- Join ------------------------------------------------------------------------

void JoinScreen::open() {
    const GameplaySettings& g = services_.settings().gameplay;
    name_ = services_.player_name();
    address_ = g.join_address;
    port_ = std::to_string(g.join_port);
    services_.set_lan_search(true);
}

bool JoinScreen::connect(const std::string& address, std::uint16_t port) {
    GameplaySettings& g = services_.settings().gameplay;
    if (net::valid_name(name_)) {
        g.player_name = name_;
    }
    if (is_valid_address(address)) {
        g.join_address = address;
    }
    g.join_port = port;
    services_.settings_changed();
    return services_.join_game(address, port);
}

JoinScreen::Result JoinScreen::frame(ui::Context& ctx, UiHost& host, bool modal) {
    if (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        result_ = Result::Back;
    }
    host.menu("join", rows(), 640.0f);
    const Result result = result_;
    result_ = Result::None;
    if (result != Result::None) {
        services_.set_lan_search(false);
    }
    return result;
}

ThingRows JoinScreen::rows() {
    ThingRows out;
    out.line(tr("join.title"), WinRow::Kind::Title);
    // A text field: what is typed goes to `text`.
    const auto field = [&out](std::string label, std::string* text, int max, std::string tip) {
        out.line(std::move(label), WinRow::Kind::Dim);
        WinRow& row = out.line(*text, WinRow::Kind::Input);
        row.max = max;
        row.tip = std::move(tip);
        row.act = out.add_act([text](GameSession*, const RowInput& in, RowEffects&) { *text = in.text; });
    };
    field(tr("join.name"), &name_, static_cast<int>(net::kMaxNameBytes), tr("join.name.tooltip"));
    const bool name_ok = net::valid_name(name_);
    // Games on the local network.
    out.line(tr("join.lan"), WinRow::Kind::Section);
    const std::vector<net::LanGame> games = services_.lan_games();
    if (games.empty()) {
        out.line(tr("join.lan.none"), WinRow::Kind::Dim);
    }
    for (std::size_t i = 0; i < games.size() && i < 5; ++i) {
        const net::LanGame g = games[i];
        out.buttons({out.button(tr(g.playing ? "join.lan.gamePlaying" : "join.lan.game", g.host_name, static_cast<int>(g.players),
                                   g.address),
                                tr("join.lan.tooltip"), row_run([this, g] {
                                    if (connect(g.address, g.port)) {
                                        result_ = Result::Joining;
                                    }
                                }),
                                name_ok)});
    }
    // Address and port.
    out.line(tr("join.address"), WinRow::Kind::Section);
    field(tr("join.address.tooltip"), &address_, 64, tr("join.address.tooltip"));
    field(tr("join.port.tooltip"), &port_, 5, tr("join.port.tooltip"));
    std::uint16_t port = 0;
    const bool can = name_ok && is_valid_address(address_) && parse_port(port_, port);
    RowButton go = out.button(tr("join.connect"), tr("join.connect.tooltip"), row_run([this] {
                                  std::uint16_t p = 0;
                                  if (parse_port(port_, p) && connect(address_, p)) {
                                      result_ = Result::Joining;
                                  }
                              }),
                              can, true);
    out.buttons({out.button(tr("join.back"), tr("join.back.tooltip"), row_run([this] { result_ = Result::Back; })), std::move(go)});
    out.rows.back().cls = "big";
    return out;
}

// --- Lobby ------------------------------------------------------------------------

void LobbyScreen::open() {
    name_ = services_.player_name();
    color_ = 0;
    color_chosen_ = false;
    ready_ = false;
    watch_ = false;
}

void LobbyScreen::send_info() {
    net::NetSession* net = services_.net();
    if (net == nullptr || !net::valid_name(name_)) {
        return;
    }
    if (net->role() == net::NetSession::Role::Host) {
        static_cast<net::NetHost*>(net)->set_local(name_, color_);
    } else {
        static_cast<net::NetClient*>(net)->set_info(name_, color_, ready_, watch_);
    }
    services_.settings().gameplay.player_name = name_;
    services_.settings_changed();
}

LobbyScreen::Result LobbyScreen::frame(ui::Context& ctx, UiHost& host, bool modal) {
    net::NetSession* net = services_.net();
    if (net == nullptr || net->state() == net::NetSession::State::Closed) {
        return Result::Leave;
    }
    // Each seat starts with its own color.
    if (!color_chosen_ && net->state() == net::NetSession::State::Lobby && !net->lobby().players.empty()) {
        color_chosen_ = true;
        color_ = static_cast<std::uint8_t>(net->local_slot() % net::kColors);
        send_info();
    }
    if (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        leave_ = true;
    }
    host.menu("lobby", rows(), 760.0f);
    const Result result = leave_ ? Result::Leave : Result::None;
    leave_ = false;
    return result;
}

namespace {

std::string css_color(std::uint8_t index) {
    return std::format("#{:06x}", kPlayerColors[index % net::kColors]);
}

}  // namespace

ThingRows LobbyScreen::rows() {
    ThingRows out;
    net::NetSession* net = services_.net();
    if (net == nullptr) {
        return out;
    }
    const bool host = net->role() == net::NetSession::Role::Host;
    const net::Lobby& lobby = net->lobby();
    net::NetHost* h = host ? static_cast<net::NetHost*>(net) : nullptr;
    out.line(tr(host ? "lobby.title.host" : "lobby.title.client"), WinRow::Kind::Title);
    // The seats, each with its color and whether it is ready.
    const auto seats = [&](bool saved) {
        std::string list = "<div class=\"seats\">";
        for (const net::LobbyPlayer& p : lobby.players) {
            const std::string name = p.slot == net->local_slot() ? tr("lobby.player.you", p.name) : p.name;
            // Whoever is not here yet may come later: the town works alone.
            const char* state = !p.connected ? (saved ? "lobby.player.saved" : "lobby.player.away")
                                : p.watching ? "lobby.player.watching"
                                : p.ready    ? "lobby.player.ready"
                                             : "lobby.player.notReady";
            list += "<div class=\"seat\"><div class=\"swatch\" style=\"background-color: " + css_color(p.color) +
                    ";\"></div><span class=\"who\">" + rml_escape(name) + "</span><span class=\"state" +
                    std::string(p.connected && p.ready ? " on" : "") + "\">" + rml_escape(tr(state)) + "</span></div>";
        }
        out.line(list + "</div>", WinRow::Kind::Raw);
    };
    // A change of the game's configuration, by the host.
    const auto config = [h](std::function<void(net::GameConfig&, int)> change) {
        return [h, change](int value) {
            if (h != nullptr) {
                net::GameConfig cfg = h->lobby().config;
                change(cfg, value);
                h->set_config(cfg);
            }
        };
    };
    if (net->state() == net::NetSession::State::Connecting) {
        out.line(tr("lobby.connecting"));
    } else if (lobby.saved) {
        // Phase 78: a saved game. Nothing of it can be changed here; each
        // seat is its player's, by name. The host says who else may come.
        out.line(tr("lobby.saved.title"), WinRow::Kind::Section);
        out.line(tr("lobby.saved.note"), WinRow::Kind::Dim);
        out.line(tr(host ? "lobby.saved.note.host" : "lobby.saved.note.client"), WinRow::Kind::Dim);
        if (const int now = services_.saved_access(); host && now >= 0) {
            struct Row {
                const char* label;
                std::uint8_t bit;
                bool enabled;
            };
            const bool open = (now & sim::access::kOpen) != 0;
            const Row access[] = {{"access.open", sim::access::kOpen, true},
                                  {"access.join", sim::access::kJoin, open},
                                  {"access.found", sim::access::kFound, open},
                                  {"access.watch", sim::access::kWatch, true}};
            for (const Row& r : access) {
                const std::uint8_t bit = r.bit;
                row_tick(out, tr(r.label), tr(std::string(r.label) + ".tooltip"), (now & r.bit) != 0, r.enabled,
                         [this, bit](bool v) {
                             const int a = services_.saved_access();
                             if (a >= 0) {
                                 services_.set_access(static_cast<std::uint8_t>(v ? a | bit : a & ~bit));
                             }
                         });
            }
        }
        seats(true);
    } else {
        // The map and the world mode.
        out.line(tr("lobby.map", std::to_string(lobby.config.map.seed),
                    tr(map_size_text_key(lobby.config.map.size), sim::map_cells(lobby.config.map.size))),
                 WinRow::Kind::Dim);
        // Many villagers in all: a warning (phase 20, docs/RENDIMIENTO.md).
        const auto count = static_cast<std::int32_t>(lobby.players.size());
        if (count * lobby.config.rules.max_population > sim::kPopulationWarning) {
            WinRow& w = out.line(tr("lobby.heavy", count * lobby.config.rules.max_population));
            w.cls = "bad";
            w.tip = tr("lobby.heavy.tooltip");
        }
        row_pick(out, tr("lobby.world"), tr("lobby.world.tooltip"),
                 {tr("lobby.world.shared"), tr("lobby.world.towns"), tr("lobby.world.separate")},
                 lobby.config.shared_town ? 0 : lobby.config.map.separate ? 2 : 1, host,
                 config([](net::GameConfig& cfg, int m) {
                     cfg.shared_town = m == 0;
                     cfg.map.separate = m == 2;
                 }));
        // The people of every town (phase 19), chosen by the host.
        if (const sim::Content* content = services_.content(); content != nullptr && !content->races.empty()) {
            std::vector<std::string> peoples;
            for (const sim::RaceDef& r : content->races) {
                peoples.push_back(tr(r.name_key));
            }
            peoples.push_back(tr("newGame.race.mixed"));
            const std::uint8_t current = lobby.config.rules.races[0];
            const int races = static_cast<int>(content->races.size());
            const int people = current == sim::kMixedRace || current >= content->races.size() ? races : current;
            row_pick(out, tr("newGame.race"), tr("lobby.race.tooltip"), peoples, people, host,
                     config([races](net::GameConfig& cfg, int p) {
                         cfg.rules.races.fill(p >= races ? sim::kMixedRace : static_cast<std::uint8_t>(p));
                     }));
        }
        // Cooperative or versus, and how a versus game is won.
        const sim::GameRules& rules = lobby.config.rules;
        int kind = 0;
        if (rules.versus) {
            kind = !rules.pvp                                  ? 1
                   : rules.victory == sim::Victory::Elimination ? 2
                   : rules.victory == sim::Victory::Score       ? 3
                   : rules.victory == sim::Victory::Objective   ? 4
                                                                : 5;
        }
        row_pick(out, tr("lobby.versus"), tr("lobby.versus.tooltip"),
                 {tr("lobby.versus.coop"), tr("lobby.versus.peace"), tr("lobby.versus.elimination"), tr("lobby.versus.score"),
                  tr("lobby.versus.objective"), tr("lobby.versus.free")},
                 kind, host, config([](net::GameConfig& cfg, int k) {
                     static constexpr sim::Victory kVictory[] = {sim::Victory::None,  sim::Victory::Score,
                                                                 sim::Victory::Elimination, sim::Victory::Score,
                                                                 sim::Victory::Objective, sim::Victory::None};
                     cfg.rules.versus = k != 0;
                     cfg.rules.pvp = k >= 2;
                     cfg.rules.victory = kVictory[k];
                 }));
        // The fog of war (phase 32).
        row_pick(out, tr("newGame.fog"), tr("newGame.fog.tooltip"),
                 {tr("newGame.fog.none"), tr("newGame.fog.static"), tr("newGame.fog.dynamic"), tr("newGame.fog.revealed")},
                 static_cast<int>(lobby.config.rules.fog), host,
                 config([](net::GameConfig& cfg, int f) { cfg.rules.fog = static_cast<sim::FogMode>(f); }));
        // Phase 79: spectators. The host says whether people may watch;
        // each of the others, whether to watch instead of playing.
        if (h != nullptr) {
            row_tick(out, tr("access.watch"), tr("access.watch.tooltip"), lobby.config.spectators, true, [h](bool v) {
                net::GameConfig cfg = h->lobby().config;
                cfg.spectators = v;
                h->set_config(cfg);
            });
        } else if (lobby.config.spectators) {
            row_tick(out, tr("lobby.watch.me"), tr("lobby.watch.me.tooltip"), watch_, true, [this](bool v) {
                watch_ = v;
                send_info();
            });
        } else {
            out.line(tr("lobby.watch.off"), WinRow::Kind::Dim);
        }
        // This player's name and color.
        out.line(tr("lobby.you"), WinRow::Kind::Section);
        WinRow& name = out.line(name_, WinRow::Kind::Input);
        name.max = static_cast<int>(net::kMaxNameBytes);
        name.tip = tr("join.name.tooltip");
        name.act = out.add_act([this](GameSession*, const RowInput& in, RowEffects&) {
            name_ = in.text;
            if (net::valid_name(name_)) {
                send_info();
            }
        });
        const int color_act = out.add_act(row_run([this] {
            color_ = static_cast<std::uint8_t>((color_ + 1) % net::kColors);
            color_chosen_ = true;
            send_info();
        }));
        out.line(std::format("<div class=\"btn colorpick\" data-act=\"{}\" tip=\"{}\"><div class=\"swatch\" "
                             "style=\"background-color: {};\"></div><span>{}</span></div>",
                             color_act, rml_escape(tr("lobby.color.tooltip")), css_color(color_),
                             rml_escape(tr("lobby.color.tooltip"))),
                 WinRow::Kind::Raw);
        seats(false);
    }
    // Buttons: leave, and start (host) or ready (client).
    std::vector<RowButton> buttons;
    buttons.push_back(out.button(tr("lobby.leave"), tr("lobby.leave.tooltip"), row_run([this] { leave_ = true; })));
    if (h != nullptr) {
        buttons.push_back(out.button(tr("lobby.start"), tr(h->can_start() ? "lobby.start.tooltip" : "lobby.start.waiting"),
                                     row_run([h] { (void)h->start(); }), h->can_start(), true));
    } else if (net->state() == net::NetSession::State::Lobby) {
        buttons.push_back(out.button(tr(ready_ ? "lobby.notReady" : "lobby.ready"), tr("lobby.ready.tooltip"), row_run([this] {
                                         ready_ = !ready_;
                                         send_info();
                                     }),
                                     true, !ready_));
    }
    out.buttons(std::move(buttons));
    out.rows.back().cls = "big";
    return out;
}

}  // namespace sc
