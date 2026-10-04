// Founding the town (phase 74): what the interface shows while the local
// player has no town yet, and while the game waits for the other founders.
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

void GameHud::founding(ui::Context& ctx, GameSession& s) {
    const sim::Game& game = s.game();
    GameSession::Interaction& ui = s.ui();
    const std::uint8_t local = s.local_player();
    const bool mine = !game.founded(local) && game.founder(local);
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
                lines.push_back({tr("hud.found.hint", key_display_name(keys.key(Action::GameRotateBuilding, 0)),
                                    key_display_name(keys.key(Action::GameNextSite, 0))),
                                 st, ctx.theme().text_dim});
            }
        }
    } else if (!game.founded(local)) {
        lines.push_back({tr("hud.found.waitingFounder", town_name(game.town_of(local))), bold, ctx.theme().text});
    }
    // Who the game still waits for.
    if (game.awaiting_founders()) {
        std::string names;
        for (std::uint8_t p = 0; p < game.player_count(); ++p) {
            if (p != local && game.founder(p) && game.player(p).active && !game.founded(p)) {
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

}  // namespace sc
