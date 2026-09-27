#include "game/multiplayer_screens.h"

#include <algorithm>
#include <charconv>
#include <cmath>

#include "game/new_game_screen.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint32_t kPlayerColors[net::kColors] = {0xD9463B, 0x3B7BD9, 0x4DAF4A, 0xE8C33A, 0x984EA3, 0xF08A24,
                                                        0x3BC1C9, 0xE377C2, 0x8C564B, 0xBCBD22, 0xF4F4F4, 0x333333};

// A centered panel of `height` for the content; returns the content box.
ui::Rect frame_panel(ui::Context& ctx, float width, float height, std::string_view title, float& y) {
    const float pad = ctx.s(24.0f);
    const ui::TextStyle ts = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const float title_h = ctx.text().line_height(ts);
    const float w = std::min(ctx.s(width), ctx.width() - ctx.s(32.0f));
    const float h = std::min(ctx.height() - ctx.s(16.0f), height + title_h + 3 * pad);
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round((ctx.height() - h) * 0.5f), std::round(w),
                       std::round(h)};
    ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().overlay);
    ctx.panel(box);
    ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, title_h}, title, ts, ctx.theme().accent);
    y = box.y + pad + title_h + pad * 0.5f;
    return {box.x + pad, y, box.w - 2 * pad, box.bottom() - pad - y};
}

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

bool JoinScreen::connect(ui::Context& ctx, const std::string& address, std::uint16_t port) {
    (void)ctx;
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

JoinScreen::Result JoinScreen::frame(ui::Context& ctx, bool modal) {
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float line = ctx.text().line_height(body);
    const float field_h = ctx.s(40.0f);
    const float gap = ctx.s(10.0f);
    const float button_h = ctx.s(44.0f);
    const std::vector<net::LanGame> games = services_.lan_games();
    const float list_h = std::max(line * 2.0f, static_cast<float>(std::min<std::size_t>(games.size(), 5)) *
                                                   (field_h + gap));
    const float content_h = (line + field_h + gap) * 2 + line + list_h + gap + button_h;
    float y = 0.0f;
    const ui::Rect c = frame_panel(ctx, 620.0f, content_h, tr("join.title"), y);
    const float label_w = std::round(c.w * 0.35f);
    Result result = Result::None;

    // Name.
    ctx.label({c.x, y, label_w, field_h}, tr("join.name"), body, ctx.theme().text);
    (void)ctx.text_field(ctx.id("join_name"), {c.x + label_w, y, c.w - label_w, field_h}, name_, net::kMaxNameBytes,
                         tr("join.name.tooltip"));
    y += field_h + gap;

    // Games on the local network.
    ctx.label({c.x, y, c.w, line}, tr("join.lan"), body, ctx.theme().text_dim);
    y += line;
    if (games.empty()) {
        ctx.label({c.x, y, c.w, line}, tr("join.lan.none"), body, ctx.theme().text_disabled);
    }
    const bool name_ok = net::valid_name(name_);
    for (std::size_t i = 0; i < games.size() && i < 5; ++i) {
        const net::LanGame& g = games[i];
        const std::string text = tr(g.playing ? "join.lan.gamePlaying" : "join.lan.game", g.host_name,
                                    static_cast<int>(g.players), g.address);
        ctx.push_id("lan");
        if (ctx.button(ctx.id(std::to_string(i)), {c.x, y, c.w, field_h}, text, tr("join.lan.tooltip"), name_ok) &&
            connect(ctx, g.address, g.port)) {
            result = Result::Joining;
        }
        ctx.pop_id();
        y += field_h + gap;
    }
    y = std::max(y, c.y + line + field_h + gap + line + list_h);

    // Address and port.
    ctx.label({c.x, y, c.w, line}, tr("join.address"), body, ctx.theme().text_dim);
    y += line;
    const float port_w = std::round(c.w * 0.22f);
    const float connect_w = std::round(c.w * 0.25f);
    const float addr_w = c.w - port_w - connect_w - 2 * gap;
    (void)ctx.text_field(ctx.id("join_address"), {c.x, y, addr_w, field_h}, address_, 64, tr("join.address.tooltip"),
                         "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-");
    (void)ctx.text_field(ctx.id("join_port"), {c.x + addr_w + gap, y, port_w, field_h}, port_, 5,
                         tr("join.port.tooltip"), "0123456789");
    std::uint16_t port = 0;
    const bool can = name_ok && is_valid_address(address_) && parse_port(port_, port);
    if (ctx.button(ctx.id("join_connect"), {c.right() - connect_w, y, connect_w, field_h}, tr("join.connect"),
                   tr("join.connect.tooltip"), can, true) &&
        connect(ctx, address_, port)) {
        result = Result::Joining;
    }
    const float bw = std::min(ctx.s(180.0f), c.w);
    if (ctx.button(ctx.id("join_back"), {c.right() - bw, c.bottom() - button_h, bw, button_h}, tr("join.back"),
                   tr("join.back.tooltip")) ||
        (!modal && !ctx.typing() && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        result = Result::Back;
    }
    if (result != Result::None) {
        services_.set_lan_search(false);
    }
    return result;
}

// --- Lobby ------------------------------------------------------------------------

void LobbyScreen::open() {
    name_ = services_.player_name();
    color_ = 0;
    color_chosen_ = false;
    ready_ = false;
}

void LobbyScreen::send_info() {
    net::NetSession* net = services_.net();
    if (net == nullptr || !net::valid_name(name_)) {
        return;
    }
    if (net->role() == net::NetSession::Role::Host) {
        static_cast<net::NetHost*>(net)->set_local(name_, color_);
    } else {
        static_cast<net::NetClient*>(net)->set_info(name_, color_, ready_);
    }
    services_.settings().gameplay.player_name = name_;
    services_.settings_changed();
}

LobbyScreen::Result LobbyScreen::frame(ui::Context& ctx, bool modal) {
    net::NetSession* net = services_.net();
    if (net == nullptr || net->state() == net::NetSession::State::Closed) {
        return Result::Leave;
    }
    const bool host = net->role() == net::NetSession::Role::Host;
    const net::Lobby& lobby = net->lobby();
    // Each seat starts with its own color.
    if (!color_chosen_ && net->state() == net::NetSession::State::Lobby && !lobby.players.empty()) {
        color_chosen_ = true;
        color_ = static_cast<std::uint8_t>(net->local_slot() % net::kColors);
        send_info();
    }
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float line = ctx.text().line_height(body);
    const float row_h = ctx.s(40.0f);
    const float gap = ctx.s(8.0f);
    const float button_h = ctx.s(44.0f);
    const float list_h = static_cast<float>(sim::kMaxPlayers / 2) * (row_h + gap);
    // Many villagers in all: a warning (phase 20, docs/RENDIMIENTO.md).
    const std::int32_t seats = static_cast<std::int32_t>(lobby.players.size());
    const bool heavy = seats * lobby.config.rules.max_population > sim::kPopulationWarning;
    const float content_h = line * (heavy ? 3 : 2) + gap + row_h * 4 + gap * 4 + list_h + gap + button_h;
    float y = 0.0f;
    const ui::Rect c = frame_panel(ctx, 760.0f, content_h, tr(host ? "lobby.title.host" : "lobby.title.client"), y);
    Result result = Result::None;

    if (net->state() == net::NetSession::State::Connecting) {
        ctx.label({c.x, y, c.w, line}, tr("lobby.connecting"), body, ctx.theme().text);
    } else {
        // The map and the world mode.
        ctx.label({c.x, y, c.w, line},
                  tr("lobby.map", std::to_string(lobby.config.map.seed),
                     tr(map_size_text_key(lobby.config.map.size), sim::map_cells(lobby.config.map.size))),
                  body, ctx.theme().text_dim);
        y += line;
        if (heavy) {
            ctx.label({c.x, y, c.w, line}, tr("lobby.heavy", seats * lobby.config.rules.max_population),
                      ctx.style(ctx.theme().small), ctx.theme().danger);
            ctx.tooltip_area(ctx.id("lobby_heavy"), {c.x, y, c.w, line}, tr("lobby.heavy.tooltip"));
            y += line;
        }
        y += gap;
        const float label_w = std::round(c.w * 0.3f);
        ctx.label({c.x, y, label_w, row_h}, tr("lobby.world"), body, ctx.theme().text);
        const std::string modes[] = {tr("lobby.world.shared"), tr("lobby.world.towns"), tr("lobby.world.separate")};
        int mode = lobby.config.shared_town ? 0 : lobby.config.map.separate ? 2 : 1;
        if (ctx.selector(ctx.id("lobby_world"), {c.x + label_w, y, c.w - label_w, row_h}, mode, modes,
                         tr("lobby.world.tooltip"), host)) {
            net::GameConfig cfg = lobby.config;
            cfg.shared_town = mode == 0;
            cfg.map.separate = mode == 2;
            static_cast<net::NetHost*>(net)->set_config(cfg);
        }
        y += row_h + gap;
        // Cooperative or versus, and how a versus game is won.
        {
            const std::string kinds[] = {tr("lobby.versus.coop"),      tr("lobby.versus.peace"),
                                         tr("lobby.versus.elimination"), tr("lobby.versus.score"),
                                         tr("lobby.versus.objective"),   tr("lobby.versus.free")};
            const sim::GameRules& rules = lobby.config.rules;
            int kind = 0;
            if (rules.versus) {
                kind = !rules.pvp                                  ? 1
                       : rules.victory == sim::Victory::Elimination ? 2
                       : rules.victory == sim::Victory::Score       ? 3
                       : rules.victory == sim::Victory::Objective   ? 4
                                                                    : 5;
            }
            // The people of every town (phase 19), chosen by the host.
            if (const sim::Content* content = services_.content(); content != nullptr && !content->races.empty()) {
                std::vector<std::string> peoples;
                for (const sim::RaceDef& r : content->races) {
                    peoples.push_back(tr(r.name_key));
                }
                peoples.push_back(tr("newGame.race.mixed"));
                const std::uint8_t current = lobby.config.rules.races[0];
                int people = current == sim::kMixedRace || current >= content->races.size()
                                 ? static_cast<int>(content->races.size())
                                 : current;
                ctx.label({c.x, y, label_w, row_h}, tr("newGame.race"), body, ctx.theme().text);
                if (ctx.selector(ctx.id("lobby_race"), {c.x + label_w, y, c.w - label_w, row_h}, people, peoples,
                                 tr("lobby.race.tooltip"), host)) {
                    net::GameConfig cfg = lobby.config;
                    cfg.rules.races.fill(people >= static_cast<int>(content->races.size()) ? sim::kMixedRace
                                                                                           : static_cast<std::uint8_t>(people));
                    static_cast<net::NetHost*>(net)->set_config(cfg);
                }
                y += row_h + gap;
            }
            ctx.label({c.x, y, label_w, row_h}, tr("lobby.versus"), body, ctx.theme().text);
            if (ctx.selector(ctx.id("lobby_versus"), {c.x + label_w, y, c.w - label_w, row_h}, kind, kinds,
                             tr("lobby.versus.tooltip"), host)) {
                net::GameConfig cfg = lobby.config;
                static constexpr sim::Victory kVictory[] = {sim::Victory::None,        sim::Victory::Score,
                                                            sim::Victory::Elimination, sim::Victory::Score,
                                                            sim::Victory::Objective,   sim::Victory::None};
                cfg.rules.versus = kind != 0;
                cfg.rules.pvp = kind >= 2;
                cfg.rules.victory = kVictory[kind];
                static_cast<net::NetHost*>(net)->set_config(cfg);
            }
            y += row_h + gap;
        }

        // This player's name and color.
        const float name_w = std::round((c.w - label_w) * 0.6f);
        ctx.label({c.x, y, label_w, row_h}, tr("lobby.you"), body, ctx.theme().text);
        if (ctx.text_field(ctx.id("lobby_name"), {c.x + label_w, y, name_w, row_h}, name_, net::kMaxNameBytes,
                           tr("join.name.tooltip")) &&
            net::valid_name(name_)) {
            send_info();
        }
        const ui::Rect swatch{c.x + label_w + name_w + gap, y, row_h, row_h};
        if (ctx.button(ctx.id("lobby_color"), swatch, "", tr("lobby.color.tooltip"))) {
            color_ = static_cast<std::uint8_t>((color_ + 1) % net::kColors);
            color_chosen_ = true;
            send_info();
        }
        ctx.draw().rect(swatch.inset(ctx.s(6.0f)), player_color(color_));
        y += row_h + gap * 2;

        // The seats, in two columns.
        const float col_w = (c.w - gap) * 0.5f;
        for (std::size_t i = 0; i < lobby.players.size(); ++i) {
            const net::LobbyPlayer& p = lobby.players[i];
            const float x = c.x + static_cast<float>(i % 2) * (col_w + gap);
            const float ry = y + static_cast<float>(i / 2) * (row_h + gap);
            const ui::Rect row{x, ry, col_w, row_h};
            ctx.draw().rect(row, ctx.theme().button_active.with_alpha(0.7f));
            ctx.draw().rect({row.x + gap, row.y + gap, row_h - 2 * gap, row_h - 2 * gap}, player_color(p.color));
            std::string name = p.name;
            if (p.slot == net->local_slot()) {
                name = tr("lobby.player.you", p.name);
            }
            const char* state = !p.connected ? "lobby.player.away" : (p.ready ? "lobby.player.ready" : "lobby.player.notReady");
            ctx.label({row.x + row_h, row.y, row.w - row_h - gap, row.h}, name, body, ctx.theme().text);
            ctx.label({row.x + row_h, row.y, row.w - row_h - gap, row.h}, tr(state), body,
                      p.ready ? ctx.theme().accent : ctx.theme().text_dim, ui::Align::Right);
        }
        y += list_h + gap;
    }

    // Buttons: leave, and start (host) or ready (client).
    const float bw = std::min(ctx.s(200.0f), (c.w - gap) * 0.5f);
    const ui::Rect leave{c.x, c.bottom() - button_h, bw, button_h};
    const ui::Rect main{c.right() - bw, c.bottom() - button_h, bw, button_h};
    if (ctx.button(ctx.id("lobby_leave"), leave, tr("lobby.leave"), tr("lobby.leave.tooltip")) ||
        (!modal && !ctx.typing() && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        result = Result::Leave;
    }
    if (host) {
        auto* h = static_cast<net::NetHost*>(net);
        if (ctx.button(ctx.id("lobby_start"), main, tr("lobby.start"),
                       tr(h->can_start() ? "lobby.start.tooltip" : "lobby.start.waiting"), h->can_start(), true)) {
            (void)h->start();
        }
    } else if (net->state() == net::NetSession::State::Lobby) {
        if (ctx.button(ctx.id("lobby_ready"), main, tr(ready_ ? "lobby.notReady" : "lobby.ready"),
                       tr("lobby.ready.tooltip"), true, !ready_)) {
            ready_ = !ready_;
            send_info();
        }
    }
    return result;
}

}  // namespace sc
