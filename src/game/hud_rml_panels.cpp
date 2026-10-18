// The game's panels in RmlUi (phase 125): what is not a window but asks or
// tells something over the map: the town's question, a speed vote, whom the
// game waits for, founding and arriving (hud_founding.cpp), the spectator's
// strip, the tutorial and the end of the game (ui_host.cpp). Each is a
// hud/panel.rml#<id> with rows of thing_rows.h, given again every frame it
// stays; under the top bar (one below the other), above the build bar or in
// the middle of the screen.
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

namespace {

// The panels under the top bar, from the top down.
constexpr std::array<const char*, 7> kTopOrder = {"spectator", "waiting", "found", "arrival", "question", "join", "vote"};

std::size_t top_rank(const std::string& id) {
    const auto it = std::find(kTopOrder.begin(), kTopOrder.end(), id);
    return static_cast<std::size_t>(it - kTopOrder.begin());
}

}  // namespace

TownNames GameHud::town_names() const {
    return [this](std::uint8_t p) { return town_name(p); };
}

void GameHud::panel(const std::string& id, ThingRows rows, PanelPlace place, float width) {
    RmlPanel& p = panels_[id];
    p.view = std::move(rows);
    p.place = place;
    p.width = width;
    p.given = true;
}

void GameHud::rml_panels(ui::Context& ctx, GameSession& s) {
    (void)s;
    rml::RmlUi* rml = services_.rml();
    if (rml == nullptr) {
        panels_.clear();
        return;
    }
    // Those not given since the last frame go.
    for (auto it = panels_.begin(); it != panels_.end();) {
        if (!it->second.given) {
            if (!it->second.doc.empty()) {
                (void)rml->show_document(it->second.doc, false);
            }
            it = panels_.erase(it);
        } else {
            ++it;
        }
    }
    std::vector<std::string> ids;
    for (const auto& [id, p] : panels_) {
        ids.push_back(id);
    }
    std::stable_sort(ids.begin(), ids.end(), [](const std::string& a, const std::string& b) { return top_rank(a) < top_rank(b); });
    float top = std::round(top_bar_bottom_ + ctx.s(10.0f));
    for (const std::string& id : ids) {
        RmlPanel& p = panels_[id];
        p.given = false;
        p.doc = "hud/panel.rml#" + id;
        if (!rml->document_shown(p.doc)) {
            (void)rml->show_document(p.doc, true);
        }
        Rml::ElementDocument* doc = rml->document(p.doc);
        if (doc == nullptr) {
            continue;
        }
        if (doc != p.attached) {
            p.attached = doc;
            p.row_keys.clear();
            for (const char* type : {"click", "change"}) {
                doc->AddEventListener(type, this);
            }
        }
        rows_into(doc->GetElementById("rows"), p.view, p.row_keys);
        const float w = std::round(std::min(ctx.s(p.width), ctx.width() - ctx.s(28.0f)));
        doc->SetProperty("width", std::format("{:.0f}px", w));
        const float h = doc->GetBox().GetSize(Rml::BoxArea::Border).y;
        float y = top;
        switch (p.place) {
            case PanelPlace::Top:
                top += h + ctx.s(8.0f);
                break;
            case PanelPlace::Bottom: {
                // Above the build bar, in the middle: the windows keep the top.
                const float bottom = build_bar_top_ > 0.0f ? build_bar_top_ : ctx.height() - ctx.s(110.0f);
                y = bottom - h - ctx.s(12.0f);
                break;
            }
            case PanelPlace::Center: y = (ctx.height() - h) * 0.5f; break;
        }
        doc->SetProperty("left", std::format("{:.0f}px", std::round((ctx.width() - w) * 0.5f)));
        doc->SetProperty("top", std::format("{:.0f}px", std::round(std::max(0.0f, y))));
        doc->PullToFront();
    }
}

void GameHud::panel_event(Rml::Event& ev, const std::string& id) {
    GameSession* s = services_.session();
    const auto found = panels_.find(id);
    if (s == nullptr || found == panels_.end()) {
        return;
    }
    RowInput input;
    int act = -1;
    if (ev.GetType() == "change") {
        Rml::Element* e = ev.GetTargetElement();
        if (e == nullptr || !e->HasAttribute("data-act")) {
            return;
        }
        act = e->GetAttribute<int>("data-act", -1);
        input.text = ev.GetParameter<Rml::String>("value", "");
        input.enter = ev.GetParameter<bool>("linebreak", false);
        input.value = static_cast<int>(std::lround(std::strtod(e->GetAttribute<Rml::String>("value", "0").c_str(), nullptr)));
    } else if (ev.GetType() == "click") {
        for (Rml::Element* e = ev.GetTargetElement(); e != nullptr && e != ev.GetCurrentElement(); e = e->GetParentNode()) {
            if (e->HasAttribute("data-act")) {
                if (e->GetTagName() != "input") {
                    act = e->GetAttribute<int>("data-act", -1);
                }
                break;
            }
        }
    }
    if (act < 0 || static_cast<std::size_t>(act) >= found->second.view.acts.size()) {
        return;
    }
    const RowFn fn = found->second.view.acts[static_cast<std::size_t>(act)];  // A copy: it may change the panels.
    RowEffects effects;
    fn(*s, input, effects);
    if (effects.focus) {
        services_.focus_camera(effects.x, effects.z);
    }
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
            return [this, vote_id, yes](GameSession&, const RowInput&, RowEffects&) {
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
    RowButton see = out.button({}, tr("hud.ask.see"), [x, z](GameSession&, const RowInput&, RowEffects& e) {
        e.focus = true;
        e.x = x;
        e.z = z;
    });
    see.icon = "icon-eye";
    out.stepper(tr("hud.ask.turtles", static_cast<int>(asked->count)), std::move(see), RowButton{});
    out.line(tr("hud.ask.days", left), WinRow::Kind::Dim);
    const auto answer = [kind = asked->kind](std::int32_t which) {
        return [kind, which](GameSession& gs, const RowInput&, RowEffects&) {
            sim::Command c;
            c.type = sim::CommandType::AnswerHappening;
            c.def = static_cast<std::uint16_t>(kind);
            c.value = which;
            gs.issue(c);
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
