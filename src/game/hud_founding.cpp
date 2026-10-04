// Founding the town (phase 74): what the interface shows while the local
// player has no town yet, and while the game waits for the other founders.
// Phase 77: whoever arrives at a game already going chooses there between
// founding a town and asking to join one, and a town's founder answers.
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "game/game_hud.h"
#include "game/game_session.h"
#include "game/input_actions.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

bool choosing_site(const sim::Game& game, const GameSession::Interaction& ui, std::uint8_t local) {
    return !game.founded(local) && game.founder(local) && game.may_found(local) &&
           (!game.player(local).late || ui.found_mode);
}

void GameHud::founding(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    GameSession::Interaction& ui = s.ui();
    const std::uint8_t local = s.local_player();
    // A seat that came later first says what it wants (the arrival window).
    const bool seated = local < game.player_count();
    const bool arriving = seated && !game.founded(local) && game.player(local).late && !ui.found_mode;
    const bool mine = seated && choosing_site(game, ui, local);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const ui::TextStyle bold = ctx.style(ctx.theme().body, ui::FontRole::Bold);
    const KeyBindings& keys = services_.settings().input.bindings;

    // The next suggested site nobody has taken.
    const std::vector<sim::StartPosition>& sites = game.map().starts;
    if (mine && !sites.empty() && pressed(ctx, Action::GameNextSite)) {
        for (std::size_t k = 0; k < sites.size(); ++k) {
            next_site_ = (next_site_ + 1) % sites.size();
            if (!game.site_taken(next_site_)) {
                services_.focus_camera(static_cast<float>(sites[next_site_].x.raw()) / 65536.0f,
                                       static_cast<float>(sites[next_site_].z.raw()) / 65536.0f);
                break;
            }
        }
    }
    if (arriving) {
        arrival(ctx, s);
    }

    struct Line {
        std::string text;
        ui::TextStyle style;
        ui::Color color;
    };
    std::vector<Line> lines;
    if (mine) {
        lines.push_back({tr("hud.found.title"), bold, ctx.theme().text});
        if (ui.found_sent != 0) {
            lines.push_back({tr("hud.found.sending"), st, ctx.theme().text_dim});
        } else if (!ui.found_asked) {
            if (ui.hover_valid && ui.hover_error != sim::PlaceError::None) {
                lines.push_back({tr(place_error_text_key(ui.hover_error)), st, ctx.theme().danger});
            } else {
                lines.push_back({tr(game.player(local).late ? "hud.found.hint.late" : "hud.found.hint",
                                    key_display_name(keys.key(Action::GameRotateBuilding, 0)),
                                    key_display_name(keys.key(Action::GameNextSite, 0))),
                                 st, ctx.theme().text_dim});
            }
        }
    } else if (!game.founded(local) && !arriving && seated && !game.founder(local)) {
        lines.push_back({tr("hud.found.waitingFounder", town_name(game.town_of(local))), bold, ctx.theme().text});
    } else if (!seated) {
        lines.push_back({tr("hud.arrive.entering"), bold, ctx.theme().text});  // The seat is on its way.
    }
    // Who the game still waits for.
    if (game.awaiting_founders()) {
        std::string names;
        for (std::uint8_t p = 0; p < game.player_count(); ++p) {
            if (p != local && game.founder(p) && game.player(p).active && !game.founded(p) && !game.player(p).late) {
                names += (names.empty() ? "" : ", ") + town_name(p);
            }
        }
        if (game.founded(local)) {
            lines.push_back({tr("hud.found.paused"), bold, ctx.theme().text});
        }
        if (!names.empty()) {
            lines.push_back({tr("hud.found.missing", names), st, ctx.theme().text_dim});
        }
    }
    if (lines.empty()) {
        return;
    }
    const float pad = ctx.s(12.0f);
    const float line_h = ctx.text().line_height(st) + ctx.s(4.0f);
    float w = 0.0f;
    for (const Line& l : lines) {
        w = std::max(w, ctx.text().measure(l.style, l.text));
    }
    w = std::min(ctx.width() - ctx.s(32.0f), w + 2 * pad);
    const float h = static_cast<float>(lines.size()) * line_h + 2 * pad - ctx.s(4.0f);
    const ui::Rect banner{std::round((ctx.width() - w) * 0.5f), std::round(top_bar_bottom_ + ctx.s(52.0f)), std::round(w),
                          std::round(h)};
    ctx.draw().rect(banner, ctx.theme().tooltip.with_alpha(0.88f));
    block(s, banner);
    float y = banner.y + pad;
    for (const Line& l : lines) {
        ctx.label({banner.x + pad, y, banner.w - 2 * pad, line_h - ctx.s(4.0f)}, l.text, l.style, l.color, ui::Align::Center);
        y += line_h;
    }

    // A site was clicked: the question. The site cannot be changed later.
    if (mine && ui.found_asked && ui.found_sent == 0) {
        const std::string q = tr("hud.found.question");
        const float bh = std::round(ctx.s(36.0f));
        const float qw = std::min(ctx.width() - 2 * pad, std::max(ctx.s(380.0f), ctx.text().measure(st, q) + 2 * pad));
        const float qh = ctx.text().line_height(st) + bh + 3 * pad;
        const ui::Rect box{std::round((ctx.width() - qw) * 0.5f), std::round(banner.bottom() + ctx.s(10.0f)), std::round(qw),
                           std::round(qh)};
        ctx.panel(box);
        block(s, box);
        ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, ctx.text().line_height(st)}, q, st, ctx.theme().text,
                  ui::Align::Center);
        const float bw = (box.w - 3 * pad) * 0.5f;
        const float by = box.bottom() - pad - bh;
        if (ctx.button(ctx.id("found_yes"), {box.x + pad, by, bw, bh}, tr("hud.found.confirm"), {}, true, true)) {
            sim::Command c;
            c.type = sim::CommandType::FoundTown;
            c.position = {sim::Fixed::from_int(ui.found_x), sim::Fixed::from_int(ui.found_z)};
            c.value = ui.found_rotation;
            s.issue(c);
            ui.found_asked = false;
            ui.found_sent = game.turn() + 1;
        } else if (ctx.button(ctx.id("found_no"), {box.x + 2 * pad + bw, by, bw, bh}, tr("hud.found.cancel"))) {
            ui.found_asked = false;
        }
    }
}

// Phase 77. The window of somebody who arrives at a game already going:
// found a town, or ask to join one (its founder decides), as the host allows.
void GameHud::arrival(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    GameSession::Interaction& ui = s.ui();
    const std::uint8_t local = s.local_player();
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const ui::TextStyle title = ctx.style(ctx.theme().heading, ui::FontRole::Bold);
    const bool can_found = game.may_found(local);
    const bool can_join = (game.access() & sim::access::kJoin) != 0;
    const std::uint8_t asked = game.player(local).request;
    std::vector<std::uint8_t> towns;
    for (std::uint8_t p = 0; p < game.player_count() && can_join; ++p) {
        if (game.town_exists(p) && game.player(p).outcome == sim::Outcome::Playing) {
            towns.push_back(p);
        }
    }
    const float pad = ctx.s(14.0f);
    const float gap = ctx.s(8.0f);
    const float bh = std::round(ctx.s(40.0f));
    const float line = ctx.text().line_height(st);
    const float title_h = ctx.text().line_height(title);
    const float w = std::round(std::min(ctx.width() - 2 * pad, ctx.s(520.0f)));
    float h = pad + title_h + gap;
    h += can_found ? bh + gap : 0.0f;
    h += can_join ? line + gap + (towns.empty() ? line + gap : static_cast<float>(towns.size()) * (bh + gap)) : 0.0f;
    h += !can_found && !can_join ? 2 * line + gap : 0.0f;
    h += ctx.text().line_height(small) + pad;
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round(top_bar_bottom_ + ctx.s(60.0f)), w, std::round(h)};
    ctx.panel(box);
    block(s, box);
    ctx.push_id("arrival");
    float y = box.y + pad;
    ctx.label({box.x + pad, y, box.w - 2 * pad, title_h}, tr("hud.arrive.title"), title, ctx.theme().accent);
    y += title_h + gap;
    if (can_found) {
        if (ctx.button(ctx.id("found"), {box.x + pad, std::round(y), box.w - 2 * pad, bh}, tr("hud.arrive.found"),
                       tr("hud.arrive.found.tooltip"), true, true)) {
            ui.found_mode = true;
        }
        y += bh + gap;
    }
    if (can_join) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.arrive.towns"), st, ctx.theme().text);
        y += line + gap;
        if (towns.empty()) {
            ctx.label({box.x + pad, y, box.w - 2 * pad, line}, tr("hud.arrive.noTowns"), st, ctx.theme().text_dim);
            y += line + gap;
        }
        const float button_w = std::round(ctx.s(170.0f));
        for (const std::uint8_t t : towns) {
            const ui::Rect row{box.x + pad, std::round(y), box.w - 2 * pad, bh};
            const bool waiting = asked == t;
            ctx.label({row.x, row.y, row.w - button_w - gap, bh},
                      waiting ? tr("hud.arrive.waiting", town_name(t)) : tr("hud.arrive.town", town_name(t)),
                      st, waiting ? ctx.theme().accent : ctx.theme().text);
            const ui::Rect button{row.right() - button_w, row.y, button_w, bh};
            sim::Command c;
            if (waiting) {
                if (ctx.button(ctx.id("cancel" + std::to_string(t)), button, tr("hud.arrive.cancel"))) {
                    c.type = sim::CommandType::CancelJoin;
                    s.issue(c);
                }
            } else if (ctx.button(ctx.id("ask" + std::to_string(t)), button, tr("hud.arrive.ask"),
                                  tr("hud.arrive.ask.tooltip", town_name(t)), asked == sim::kNoRequest)) {
                c.type = sim::CommandType::RequestJoin;
                c.count = t;
                s.issue(c);
            }
            y += bh + gap;
        }
    }
    if (!can_found && !can_join) {
        ctx.label({box.x + pad, y, box.w - 2 * pad, 2 * line}, tr("hud.arrive.none"), st, ctx.theme().text_dim);
        y += 2 * line + gap;
    }
    ctx.label({box.x + pad, y, box.w - 2 * pad, ctx.text().line_height(small)}, tr("hud.arrive.note"), small,
              ctx.theme().text_dim);
    ctx.pop_id();
}

// Phase 77. Somebody asks to join the local player's town: only its
// founder is asked, one request at a time, for as long as it stands.
void GameHud::join_requests(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    const std::uint8_t local = s.local_player();
    if (!game.town_exists(local)) {
        return;  // Not a founder (or no town yet).
    }
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.player(p).request != local) {
            continue;
        }
        // Answered a moment ago: the order is on its way.
        if (p == answered_seat_ && game.turn() < answered_turn_ + 50) {
            continue;
        }
        const ui::TextStyle st = ctx.style(ctx.theme().body);
        const std::string q = tr("hud.join.question", town_name(p));
        const float pad = ctx.s(12.0f);
        const float bh = std::round(ctx.s(36.0f));
        const float w = std::min(ctx.width() - 2 * pad, std::max(ctx.s(380.0f), ctx.text().measure(st, q) + 2 * pad));
        const float h = ctx.text().line_height(st) + bh + 3 * pad;
        const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round(top_bar_bottom_ + ctx.s(56.0f)), std::round(w),
                           std::round(h)};
        ctx.panel(box);
        block(s, box);
        ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, ctx.text().line_height(st)}, q, st, ctx.theme().text,
                  ui::Align::Center);
        const float bw = (box.w - 3 * pad) * 0.5f;
        const float by = box.bottom() - pad - bh;
        sim::Command c;
        c.count = p;
        bool answered = false;
        if (ctx.button(ctx.id("join_yes"), {box.x + pad, by, bw, bh}, tr("hud.net.accept"), tr("hud.join.accept.tooltip"), true,
                       true)) {
            c.type = sim::CommandType::JoinTown;
            answered = true;
        } else if (ctx.button(ctx.id("join_no"), {box.x + 2 * pad + bw, by, bw, bh}, tr("hud.net.refuse"))) {
            c.type = sim::CommandType::RefuseJoin;
            answered = true;
        }
        if (answered) {
            s.issue(c);
            answered_seat_ = p;
            answered_turn_ = game.turn();
        }
        return;  // One at a time.
    }
}

}  // namespace sc
