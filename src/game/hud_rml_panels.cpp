// The game's panels in RmlUi (phase 125): what is not a window but asks or
// tells something over the map: the town's question, a speed vote, whom the
// game waits for, founding and arriving (hud_founding.cpp), the spectator's
// strip, the tutorial and the end of the game (ui_host.cpp). Each is a
// hud/panel.rml#<id> with rows of thing_rows.h, given again every frame it
// stays (rml_panels.h).
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <format>

#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Event.h>

#include "game/game_hud.h"
#include "game/game_session.h"
#include "i18n/translator.h"
#include "net/lockstep.h"
#include "ui/rml/rml_ui.h"

namespace sc {

using i18n::tr;

TownNames GameHud::town_names() const {
    return [this](std::uint8_t p) { return town_name(p); };
}

void GameHud::panel(const std::string& id, ThingRows rows, PanelPlace place, float width) {
    panels_.give(id, std::move(rows), place, width);
}

void GameHud::rml_panels(ui::Context& ctx, GameSession&) {
    panels_.show(services_.rml(), ctx.width(), ctx.height(), ctx.s(1.0f), top_bar_bottom_ + ctx.s(10.0f), build_bar_top_);
}

void GameHud::network_prompts(GameSession& s) {
    net::NetSession* net = services_.net();
    if (net == nullptr || !s.networked()) {
        return;
    }
    // Waiting for somebody.
    for (const net::LobbyPlayer& p : net->lobby().players) {
        if (net->waiting_for() && *net->waiting_for() == p.slot && p.slot != net->local_slot()) {
            ThingRows out;
            out.line(tr("hud.net.waiting", p.name));
            panel("waiting", std::move(out), PanelPlace::Top, 360.0f);
        }
    }
    // A speed vote someone else asked for.
    const std::optional<net::SpeedVote>& vote = net->vote();
    if (vote && vote->from != net->local_slot() && answered_vote_ != vote->id) {
        std::string from;
        for (const net::LobbyPlayer& p : net->lobby().players) {
            from = p.slot == vote->from ? p.name : from;
        }
        ThingRows out;
        out.line(tr("hud.net.vote", from, speed_text(vote->speed)), WinRow::Kind::Paragraph);
        const std::uint32_t vote_id = vote->id;
        const auto answer = [this, vote_id](bool yes) {
            return [this, vote_id, yes](GameSession*, const RowInput&, RowEffects&) {
                if (net::NetSession* n = services_.net()) {
                    n->answer_vote(yes);
                }
                answered_vote_ = vote_id;
            };
        };
        RowButton yes = out.button(tr("hud.net.accept"), {}, answer(true));
        yes.on = true;
        out.buttons({std::move(yes), out.button(tr("hud.net.refuse"), {}, answer(false))});
        panel("vote", std::move(out), PanelPlace::Top, 420.0f);
    }
}

// Phase 114: what a happening asks the town: the question and its two
// answers, under the top bar, for as long as it waits. Any seat of the town
// answers, and the answer is an order like any other.
void GameHud::question(GameSession& s) {
    const sim::Game& game = s.game();
    const sim::Happening* asked = nullptr;
    for (const sim::Happening& h : game.happenings()) {
        if (h.state == sim::HappeningState::Asked && h.town == s.town() && h.kind == sim::HappeningKind::Turtles) {
            asked = &h;
            break;
        }
    }
    if (asked == nullptr) {
        return;
    }
    const auto today = static_cast<std::uint32_t>(game.calendar_day());
    const int left = asked->until_day > today ? static_cast<int>(asked->until_day - today) : 0;
    ThingRows out;
    const float x = static_cast<float>(asked->at.x.raw()) / 65536.0f;
    const float z = static_cast<float>(asked->at.z.raw()) / 65536.0f;
    RowButton see = out.button({}, tr("hud.ask.see"), [x, z](GameSession*, const RowInput&, RowEffects& e) {
        e.focus = true;
        e.x = x;
        e.z = z;
    });
    see.icon = "icon-eye";
    out.stepper(tr("hud.ask.turtles", static_cast<int>(asked->count)), std::move(see), RowButton{});
    out.line(tr("hud.ask.days", left), WinRow::Kind::Dim);
    const auto answer = [kind = asked->kind](std::int32_t which) {
        return [kind, which](GameSession* gs, const RowInput&, RowEffects&) {
            sim::Command c;
            c.type = sim::CommandType::AnswerHappening;
            c.def = static_cast<std::uint16_t>(kind);
            c.value = which;
            gs->issue(c);
        };
    };
    out.buttons({out.button(tr("hud.ask.turtles.keep"), tr("hud.ask.turtles.keep.tooltip", static_cast<int>(sim::village::kProtectDays)),
                            answer(1)),
                 out.button(tr("hud.ask.turtles.take"),
                            tr("hud.ask.turtles.take.tooltip", static_cast<int>(asked->count) * sim::village::kTurtleEggs),
                            answer(2))});
    panel("question", std::move(out), PanelPlace::Top, 520.0f);
}

}  // namespace sc
