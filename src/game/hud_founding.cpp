// Founding the town (phase 74): what the interface shows while the local
// player has no town yet, and while the game waits for the other founders.
// Phase 77: whoever arrives at a game already going chooses there between
// founding a town and asking to join one, and a town's founder answers.
// Phase 125: shown as RmlUi panels (rows of thing_rows.h).
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
        arrival(s);
    }

    ThingRows out;
    if (mine) {
        out.line(tr("hud.found.title"), WinRow::Kind::Title);
        if (ui.found_sent != 0) {
            out.line(tr("hud.found.sending"), WinRow::Kind::Dim);
        } else if (!ui.found_asked) {
            if (ui.hover_valid && ui.hover_error != sim::PlaceError::None) {
                out.line(tr(place_error_text_key(ui.hover_error))).cls = "bad";
            } else {
                out.line(tr(game.player(local).late ? "hud.found.hint.late" : "hud.found.hint",
                            key_display_name(keys.key(Action::GameRotateBuilding, 0)),
                            key_display_name(keys.key(Action::GameNextSite, 0))),
                         WinRow::Kind::Dim);
            }
        }
    } else if (!game.founded(local) && !arriving && seated && !game.founder(local)) {
        out.line(tr("hud.found.waitingFounder", town_name(game.town_of(local))), WinRow::Kind::Title);
    } else if (!seated) {
        out.line(tr("hud.arrive.entering"), WinRow::Kind::Title);  // The seat is on its way.
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
            out.line(tr("hud.found.paused"), WinRow::Kind::Title);
        }
        if (!names.empty()) {
            out.line(tr("hud.found.missing", names), WinRow::Kind::Dim);
        }
    }
    // A site was clicked: the question. The site cannot be changed later.
    if (mine && ui.found_asked && ui.found_sent == 0) {
        out.line(tr("hud.found.question"), WinRow::Kind::Paragraph);
        RowButton yes = out.button(tr("hud.found.confirm"), {}, [](GameSession* gs, const RowInput&, RowEffects&) {
            GameSession::Interaction& u = gs->ui();
            if (!u.found_asked) {
                return;
            }
            sim::Command c;
            c.type = sim::CommandType::FoundTown;
            c.position = {sim::Fixed::from_int(u.found_x), sim::Fixed::from_int(u.found_z)};
            c.value = u.found_rotation;
            gs->issue(c);
            u.found_asked = false;
            u.found_sent = gs->game().turn() + 1;
        });
        yes.on = true;
        out.buttons({std::move(yes), out.button(tr("hud.found.cancel"), {}, [](GameSession* gs, const RowInput&, RowEffects&) {
                         gs->ui().found_asked = false;
                     })});
    }
    if (!out.rows.empty()) {
        panel("found", std::move(out), PanelPlace::Top, 520.0f);
    }
}

// Phase 77. The window of somebody who arrives at a game already going:
// found a town, or ask to join one (its founder decides), as the host allows.
void GameHud::arrival(GameSession& s) {
    const sim::Game& game = s.game();
    const std::uint8_t local = s.local_player();
    // Phase 79: a spectator has no seat yet. It gets one when it chooses.
    const bool visitor = s.spectating();
    const bool can_found = visitor ? game.open() && (game.access() & sim::access::kFound) != 0 : game.may_found(local);
    const bool can_join = (game.access() & sim::access::kJoin) != 0 && (!visitor || game.open());
    const std::uint8_t asked = visitor ? sim::kNoRequest : game.player(local).request;
    std::vector<std::uint8_t> towns;
    for (std::uint8_t p = 0; p < game.player_count() && can_join; ++p) {
        if (game.town_exists(p) && game.player(p).outcome == sim::Outcome::Playing) {
            towns.push_back(p);
        }
    }
    ThingRows out;
    out.line(tr(visitor ? "hud.arrive.title.watching" : "hud.arrive.title"), WinRow::Kind::Title);
    if (can_found) {
        RowButton found = out.button(tr("hud.arrive.found"), tr("hud.arrive.found.tooltip"),
                                     [this, visitor](GameSession* gs, const RowInput&, RowEffects&) {
                                         if (visitor) {
                                             services_.play_game(-1);  // A seat first; then the site.
                                         } else {
                                             gs->ui().found_mode = true;
                                         }
                                     });
        found.on = true;
        out.buttons({std::move(found)});
    }
    if (can_join) {
        out.line(tr("hud.arrive.towns"), WinRow::Kind::Section);
        if (towns.empty()) {
            out.line(tr("hud.arrive.noTowns"), WinRow::Kind::Dim);
        }
        for (const std::uint8_t t : towns) {
            const bool waiting = asked == t;
            if (waiting) {
                sim::Command c;
                c.type = sim::CommandType::CancelJoin;
                out.stepper(tr("hud.arrive.waiting", town_name(t)),
                            out.button(tr("hud.arrive.cancel"), {},
                                       [c](GameSession* gs, const RowInput&, RowEffects&) { gs->issue(c); }),
                            RowButton{});
                out.rows.back().cls = "accent";
            } else {
                out.stepper(tr("hud.arrive.town", town_name(t)),
                            out.button(
                                tr("hud.arrive.ask"), tr("hud.arrive.ask.tooltip", town_name(t)),
                                [this, visitor, t](GameSession* gs, const RowInput&, RowEffects&) {
                                    if (visitor) {
                                        services_.play_game(t);  // A seat first; then the request.
                                    } else {
                                        sim::Command c;
                                        c.type = sim::CommandType::RequestJoin;
                                        c.count = t;
                                        gs->issue(c);
                                    }
                                },
                                asked == sim::kNoRequest),
                            RowButton{});
            }
        }
    }
    if (!can_found && !can_join) {
        out.line(tr(visitor ? "hud.arrive.none.watching" : "hud.arrive.none"), WinRow::Kind::Paragraph);
    }
    if (visitor) {
        out.buttons({out.button(tr("hud.arrive.watch"), tr("hud.arrive.watch.tooltip"),
                                [](GameSession* gs, const RowInput&, RowEffects&) { gs->ui().arrival_open = false; })});
    }
    out.line(tr("hud.arrive.note"), WinRow::Kind::Dim);
    panel("arrival", std::move(out), PanelPlace::Top, 520.0f);
}

// Phase 79. The strip of whoever watches: what it looks at (everything
// without fog, or what one town sees) and how to play.
void GameHud::spectator(GameSession& s) {
    const sim::Game& game = s.game();
    std::vector<std::uint8_t> towns;
    int index = 0;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_exists(p)) {
            towns.push_back(p);
            if (!s.view_all() && game.town_of(s.local_player()) == p) {
                index = static_cast<int>(towns.size());
            }
        }
    }
    const bool mine = s.seat() != GameSession::kNoSeat;
    ThingRows out;
    // Everything, or as one town: the arrows go through them.
    const int count = static_cast<int>(towns.size()) + 1;
    const auto show = [towns](GameSession& gs, int i) {
        if (i <= 0 || i > static_cast<int>(towns.size())) {
            gs.watch(gs.local_player(), true, gs.seat());
        } else {
            gs.watch(towns[static_cast<std::size_t>(i - 1)], false, gs.seat());
        }
    };
    RowButton prev = out.button({}, tr("hud.watch.tooltip"), [show, index, count](GameSession* gs, const RowInput&, RowEffects&) {
        if (gs != nullptr) {
            show(*gs, (index + count - 1) % count);
        }
    });
    prev.icon = "icon-left";
    RowButton next = out.button({}, tr("hud.watch.tooltip"), [show, index, count](GameSession* gs, const RowInput&, RowEffects&) {
        if (gs != nullptr) {
            show(*gs, (index + 1) % count);
        }
    });
    next.icon = "icon-right";
    out.stepper(tr("hud.watch.label") + " " +
                    (index <= 0 ? tr("hud.watch.all") : tr("hud.watch.as", town_name(towns[static_cast<std::size_t>(index - 1)]))),
                std::move(prev), std::move(next));
    if (mine || game.open()) {
        out.buttons({out.button(tr(mine ? "hud.watch.back" : "hud.watch.play"),
                                tr(mine ? "hud.watch.back.tooltip" : "hud.watch.play.tooltip"),
                                [this, mine](GameSession* gs, const RowInput&, RowEffects&) {
                                    if (mine) {
                                        services_.play_game(0);
                                    } else {
                                        gs->ui().arrival_open = !gs->ui().arrival_open;
                                    }
                                })});
    }
    panel("spectator", std::move(out), PanelPlace::Top, 460.0f);
}

// Phase 77. Somebody asks to join the local player's town: only its
// founder is asked, one request at a time, for as long as it stands.
void GameHud::join_requests(GameSession& s) {
    const sim::Game& game = s.game();
    // The town this player founded, whatever it is looking at now.
    const std::uint8_t local = s.spectating() ? s.seat() : s.local_player();
    if (local == GameSession::kNoSeat || !game.town_exists(local)) {
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
        ThingRows out;
        out.line(tr("hud.join.question", town_name(p)), WinRow::Kind::Paragraph);
        if (s.spectating()) {
            // Phase 79: watching, the founder sees it but answers from its town.
            out.buttons({out.button(tr("hud.watch.backToAnswer"), {},
                                    [this](GameSession*, const RowInput&, RowEffects&) { services_.play_game(0); })});
        } else {
            const auto answer = [this, p](sim::CommandType type) {
                return [this, p, type](GameSession* gs, const RowInput&, RowEffects&) {
                    sim::Command c;
                    c.type = type;
                    c.count = p;
                    gs->issue(c);
                    answered_seat_ = p;
                    answered_turn_ = gs->game().turn();
                };
            };
            RowButton yes = out.button(tr("hud.net.accept"), tr("hud.join.accept.tooltip"), answer(sim::CommandType::JoinTown));
            yes.on = true;
            out.buttons({std::move(yes), out.button(tr("hud.net.refuse"), {}, answer(sim::CommandType::RefuseJoin))});
        }
        panel("join", std::move(out), PanelPlace::Top, 440.0f);
        return;  // One at a time.
    }
}

}  // namespace sc
